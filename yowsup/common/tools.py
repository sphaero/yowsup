import time,datetime,re, hashlib
from dateutil import tz
import os
from .constants import YowConstants
import codecs, sys
import json
import logging
import tempfile
import base64
import hashlib
import os.path, mimetypes
from pkg_resources import resource_string
from subprocess import CalledProcessError, check_output

logger = logging.getLogger(__name__)

class Jid:
    @staticmethod
    def normalize(number):
        if '@' in number:
            return number
        elif "-" in number:
            return "%s@%s" % (number, YowConstants.WHATSAPP_GROUP_SERVER)
        return "%s@%s" % (number, YowConstants.WHATSAPP_SERVER)

class HexTools:
    decode_hex = codecs.getdecoder("hex_codec")
    @staticmethod
    def decodeHex(hexString):
        result = HexTools.decode_hex(hexString)[0]
        if sys.version_info >= (3,0):
            result = result.decode('latin-1')
        return result

class WATools:
    @staticmethod
    def generateIdentity():
        return os.urandom(20)

    @staticmethod
    def getFileHashForUpload(filePath):
        sha1 = hashlib.sha256()
        f = open(filePath, 'rb')
        try:
            sha1.update(f.read())
        finally:
            f.close()
        b64Hash = base64.b64encode(sha1.digest())
        return b64Hash if type(b64Hash) is str else b64Hash.decode()

class StorageTools:
    @staticmethod
    def constructPath(*path):
        path = os.path.join(*path)
        fullPath = os.path.expanduser(os.path.join(YowConstants.PATH_STORAGE, path))
        if not os.path.exists(os.path.dirname(fullPath)):
            os.makedirs(os.path.dirname(fullPath))
        return fullPath

    @staticmethod
    def getStorageForPhone(phone):
        return StorageTools.constructPath(phone + '/')

    @staticmethod
    def writeIdentity(phone, identity):
        path = StorageTools.getStorageForPhone(phone)
        with open(os.path.join(path, "id"), 'wb') as idFile:
            idFile.write(identity)

    @staticmethod
    def getIdentity(phone):
        path = StorageTools.getStorageForPhone(phone)
        out = None
        idPath = os.path.join(path, "id")
        if os.path.isfile(idPath):
            with open(idPath, 'rb') as idFile:
                out = idFile.read()
        return out

    @staticmethod
    def writeNonce(phone, nonce):
        path = StorageTools.getStorageForPhone(phone)
        with open(os.path.join(path, "nonce"), 'wb') as idFile:
            idFile.write(nonce.encode("latin-1") if sys.version_info >= (3,0) else nonce)

    @staticmethod
    def getNonce(phone):
        path = StorageTools.getStorageForPhone(phone)
        out = None
        noncePath = os.path.join(path, "nonce")
        if os.path.isfile(noncePath):
            with open(noncePath, 'rb') as idFile:
                out = idFile.read()
        return out

class TimeTools:
    @staticmethod
    def parseIso(iso):
        d=datetime.datetime(*map(int, re.split('[^\d]', iso)[:-1]))
        return d

    @staticmethod
    def utcToLocal(dt):
        utc = tz.gettz('UTC')
        local = tz.tzlocal()
        dtUtc =  dt.replace(tzinfo=utc)

        return dtUtc.astimezone(local)

    @staticmethod
    def utcTimestamp():
        #utc = tz.gettz('UTC')
        utcNow = datetime.datetime.utcnow()
        return TimeTools.datetimeToTimestamp(utcNow)

    @staticmethod
    def datetimeToTimestamp(dt):
        return time.mktime(dt.timetuple())


class ModuleTools:
    @staticmethod
    def INSTALLED_FFVIDEO():
        try:
            import ffvideo
            return True
        except ImportError:
            return False
    @staticmethod
    def INSTALLED_EXIFTOOL():
        try:
            check_output(["exiftool", "-ver"])
            return True
        except OSError:
            return False
    @staticmethod
    def INSTALLED_PIL():
        try:
            import PIL
            return True
        except ImportError:
            return False
    @staticmethod
    def INSTALLED_AXOLOTL():
        try:
            import axolotl
            return True
        except ImportError:
            return False

class ImageTools:

    @staticmethod
    def scaleImage(infile, outfile, imageFormat, width, height):
        if ModuleTools.INSTALLED_PIL():
            from PIL import Image
            im = Image.open(infile)
            #Convert P mode images
            if im.mode != "RGB":
                im = im.convert("RGB")
            im.thumbnail((width, height))
            im.save(outfile, imageFormat)
            return True
        else:
            logger.warn("Python PIL library not installed")
            return False


    @staticmethod
    def getImageDimensions(imageFile):
        if ModuleTools.INSTALLED_PIL():
            from PIL import Image
            im = Image.open(imageFile)
            return im.size
        else:
            logger.warn("Python PIL library not installed")

    @staticmethod
    def generatePreviewFromImage(image):
        fd, path = tempfile.mkstemp()
        
        preview = None
        if ImageTools.scaleImage(image, path, "JPEG", YowConstants.PREVIEW_WIDTH, YowConstants.PREVIEW_HEIGHT):
            fileObj = os.fdopen(fd, "rb+")
            fileObj.seek(0)
            preview = fileObj.read()
            fileObj.close()
        os.remove(path)
        return preview

class MimeTools:
    MIME_FILE = resource_string(__name__, 'mime.types')
    mimetypes.init() # Load default mime.types
    try:
        mimetypes.init([MIME_FILE]) # Append whatsapp mime.types
    except exception as e:
        logger.warning("Mime types supported can't be read. System mimes will be used. Cause: " + e.message)

    @staticmethod
    def getMIME(filepath):
        mimeType = mimetypes.guess_type(filepath)[0]
        if mimeType is None:
            raise Exception("Unsupported/unrecognized file type for: "+filepath);
        return mimeType

    @staticmethod
    def getExtension(mimetype):
        ext = mimetypes.guess_extension(mimetype.split(';')[0])
        if ext is None:
            raise Exception("Unsupported/unrecognized mimetype: "+mimetype);
        return ext


class VideoTools:
    
    @staticmethod
    def getVideoProperties(videoFile):
        if ModuleTools.INSTALLED_FFVIDEO():
            from ffvideo import VideoStream
            s = VideoStream(videoFile)
            return s.width, s.height, s.bitrate, s.duration #, s.codec_name
        elif ModuleTools.INSTALLED_EXIFTOOL():
            try:
                result = json.loads(check_output(["exiftool", "-j", "-n", videoFile]))[0]
            except CalledProcessError:
                logger.warn("exiftool returned non-zero status for video %s", videoFile)
            except (IndexError, ValueError):
                logger.warn("Failed reading exiftool result for video %s", videoFile)
            else:
                try:
                    return result["ImageWidth"], result["ImageHeight"], \
                            result["AvgBitrate"], result["Duration"]
                except KeyError:
                    logger.warn("Failed reading video properties from exiftool JSON")
        else:
            logger.warn("None of [Python ffvideo library, exiftool] installed")

    @staticmethod
    def generatePreviewFromVideo(videoFile):
        if ModuleTools.INSTALLED_FFVIDEO():
            from ffvideo import VideoStream
            fd, path = tempfile.mkstemp('.jpg')
            stream = VideoStream(videoFile)
            stream.get_frame_at_sec(0).image().save(path)
            preview = ImageTools.generatePreviewFromImage(path)
            os.remove(path)
            return preview      
        else:
            logger.warn("Python ffvideo library not installed")
