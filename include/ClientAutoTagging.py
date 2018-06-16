import imp
import sys
import os

class AutoTaggerException(Exception):
    pass

class Tagger( object ):
    def __init__( self, path ):
        try:
            sys.path.insert(0, path)
            TagModuleLocation = imp.find_module('tag')
            TagModule = imp.load_module('tag', *TagModuleLocation)
            sys.path.pop(0)

            self._path = path

            self._Load = TagModule.load
            self._GetTags = TagModule.get_tags
            self._TagImage = TagModule.tag_image
            self._TagImages = TagModule.tag_images

        except ZeroDivisionError:
            raise AutoTaggerException('Given path did not contain a directory or was packaged incorrectly')
        except NameError:
            raise AutoTaggerException('Given path did not contain a tagger')

    def Load( self ):
        old_dir = os.getcwd()
        os.chdir(self._path)
        self._Load()
        os.chdir(old_dir)

    def GetTags( self ):
        return self._GetTags()

    def TagImage( self, numpy_image, threshold ):
        return self._TagImage( numpy_image, threshold )

    def TagImages( self, keys, numpy_images, threshold ):
        return self._TagImages( keys, numpy_images, threshold )

    
