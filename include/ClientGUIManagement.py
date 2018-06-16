import HydrusConstants as HC
import ClientDownloading
import HydrusExceptions
import HydrusPaths
import HydrusSerialisable
import HydrusThreading
import ClientConstants as CC
import ClientData
import ClientDefaults
import ClientCaches
import ClientFiles
import ClientGUIACDropdown
import ClientGUICanvas
import ClientGUICommon
import ClientGUIControls
import ClientGUIDialogs
import ClientGUIImport
import ClientGUIListBoxes
import ClientGUIListCtrl
import ClientGUIMedia
import ClientGUIMenus
import ClientGUIParsing
import ClientGUIScrolledPanels
import ClientGUIScrolledPanelsEdit
import ClientGUISeedCache
import ClientGUIShortcuts
import ClientGUITime
import ClientGUITopLevelWindows
import ClientImporting
import ClientImportOptions
import ClientImportWatchers
import ClientMedia
import ClientParsing
import ClientPaths
import ClientRendering
import ClientSearch
import ClientThreading
import HydrusData
import HydrusGlobals as HG
import HydrusText
import HydrusThreading
import json
import multipart
import os
import threading
import time
import traceback
import urlparse
import wx
import wx.lib.scrolledpanel

CAPTCHA_FETCH_EVENT_TYPE = wx.NewEventType()
CAPTCHA_FETCH_EVENT = wx.PyEventBinder( CAPTCHA_FETCH_EVENT_TYPE )

ID_TIMER_CAPTCHA = wx.NewId()
ID_TIMER_DUMP = wx.NewId()

MANAGEMENT_TYPE_DUMPER = 0
MANAGEMENT_TYPE_IMPORT_GALLERY = 1
MANAGEMENT_TYPE_IMPORT_SIMPLE_DOWNLOADER = 2
MANAGEMENT_TYPE_IMPORT_HDD = 3
MANAGEMENT_TYPE_IMPORT_WATCHER = 4
MANAGEMENT_TYPE_PETITIONS = 5
MANAGEMENT_TYPE_QUERY = 6
MANAGEMENT_TYPE_IMPORT_URLS = 7
MANAGEMENT_TYPE_DUPLICATE_FILTER = 8
MANAGEMENT_TYPE_IMPORT_MULTIPLE_WATCHER = 9
MANAGEMENT_TYPE_AUTO_TAGGING = 10

management_panel_types_to_classes = {}

def CreateManagementController( page_name, management_type, file_service_key = None ):
    
    if file_service_key is None:
        
        file_service_key = CC.COMBINED_LOCAL_FILE_SERVICE_KEY
        
    
    new_options = HG.client_controller.new_options
    
    management_controller = ManagementController( page_name )
    
    management_controller.SetType( management_type )
    management_controller.SetKey( 'file_service', file_service_key )
    management_controller.SetVariable( 'media_sort', new_options.GetDefaultSort() )
    
    return management_controller


def CreateManagementControllerAutoTag():

    management_controller = CreateManagementController( 'auto tag', MANAGEMENT_TYPE_AUTO_TAGGING )

    management_controller.SetVariable( 'proposed_tags', {} )
    
    return management_controller

    
def CreateManagementControllerDuplicateFilter():
    
    management_controller = CreateManagementController( 'duplicates', MANAGEMENT_TYPE_DUPLICATE_FILTER )
    
    management_controller.SetKey( 'duplicate_filter_file_domain', CC.LOCAL_FILE_SERVICE_KEY )
    
    return management_controller
    
def CreateManagementControllerImportGallery( gallery_identifier ):
    
    page_name = gallery_identifier.ToString()
    
    management_controller = CreateManagementController( page_name, MANAGEMENT_TYPE_IMPORT_GALLERY )
    
    gallery_import = ClientImporting.GalleryImport( gallery_identifier = gallery_identifier )
    
    management_controller.SetVariable( 'gallery_import', gallery_import )
    
    return management_controller
    
def CreateManagementControllerImportSimpleDownloader():
    
    management_controller = CreateManagementController( 'simple downloader', MANAGEMENT_TYPE_IMPORT_SIMPLE_DOWNLOADER )
    
    simple_downloader_import = ClientImporting.SimpleDownloaderImport()
    
    formula_name = HG.client_controller.new_options.GetString( 'favourite_simple_downloader_formula' )
    
    simple_downloader_import.SetFormulaName( formula_name )
    
    management_controller.SetVariable( 'simple_downloader_import', simple_downloader_import )
    
    return management_controller
    
def CreateManagementControllerImportHDD( paths, file_import_options, paths_to_tags, delete_after_success ):
    
    management_controller = CreateManagementController( 'import', MANAGEMENT_TYPE_IMPORT_HDD )
    
    hdd_import = ClientImporting.HDDImport( paths = paths, file_import_options = file_import_options, paths_to_tags = paths_to_tags, delete_after_success = delete_after_success )
    
    management_controller.SetVariable( 'hdd_import', hdd_import )
    
    return management_controller
    
def CreateManagementControllerImportMultipleWatcher( url = None ):
    
    management_controller = CreateManagementController( 'multiple watcher', MANAGEMENT_TYPE_IMPORT_MULTIPLE_WATCHER )
    
    multiple_watcher_import = ClientImportWatchers.MultipleWatcherImport( url = url )
    
    management_controller.SetVariable( 'multiple_watcher_import', multiple_watcher_import )
    
    return management_controller
    
def CreateManagementControllerImportWatcher( url = None ):
    
    if url is None:
        
        url = ''
        
    
    management_controller = CreateManagementController( 'watcher', MANAGEMENT_TYPE_IMPORT_WATCHER )
    
    watcher_import = ClientImportWatchers.WatcherImport()
    
    watcher_import.SetURL( url )
    
    management_controller.SetVariable( 'watcher_import', watcher_import )
    
    return management_controller
    
def CreateManagementControllerImportURLs():
    
    management_controller = CreateManagementController( 'url import', MANAGEMENT_TYPE_IMPORT_URLS )
    
    urls_import = ClientImporting.URLsImport()
    
    management_controller.SetVariable( 'urls_import', urls_import )
    
    return management_controller
    
def CreateManagementControllerPetitions( petition_service_key ):
    
    petition_service = HG.client_controller.services_manager.GetService( petition_service_key )
    
    page_name = petition_service.GetName() + ' petitions'
    
    petition_service_type = petition_service.GetServiceType()
    
    if petition_service_type in HC.LOCAL_FILE_SERVICES or petition_service_type == HC.FILE_REPOSITORY:
        
        file_service_key = petition_service_key
        
    else:
        
        file_service_key = CC.COMBINED_FILE_SERVICE_KEY
        
    
    management_controller = CreateManagementController( page_name, MANAGEMENT_TYPE_PETITIONS, file_service_key = file_service_key )
    
    management_controller.SetKey( 'petition_service', petition_service_key )
    
    return management_controller
    
def CreateManagementControllerQuery( page_name, file_service_key, file_search_context, search_enabled ):
    
    management_controller = CreateManagementController( page_name, MANAGEMENT_TYPE_QUERY, file_service_key = file_service_key )
    
    management_controller.SetVariable( 'file_search_context', file_search_context )
    management_controller.SetVariable( 'search_enabled', search_enabled )
    management_controller.SetVariable( 'synchronised', True )
    
    return management_controller
    
def CreateManagementPanel( parent, page, controller, management_controller ):
    
    management_type = management_controller.GetType()
    
    management_class = management_panel_types_to_classes[ management_type ]
    
    management_panel = management_class( parent, page, controller, management_controller )
    
    return management_panel
    
def GenerateDumpMultipartFormDataCTAndBody( fields ):
    
    m = multipart.Multipart()
    
    for ( name, field_type, value ) in fields:
        
        if field_type in ( CC.FIELD_TEXT, CC.FIELD_COMMENT, CC.FIELD_PASSWORD, CC.FIELD_VERIFICATION_RECAPTCHA, CC.FIELD_THREAD_ID ):
            
            m.field( name, HydrusData.ToByteString( value ) )
            
        elif field_type == CC.FIELD_CHECKBOX:
            
            if value:
                
                # spoiler/on -> name : spoiler, value : on
                # we don't say true/false for checkboxes
                
                ( name, value ) = name.split( '/', 1 )
                
                m.field( name, value )
                
            
        elif field_type == CC.FIELD_FILE:
            
            ( hash, mime, file ) = value
            
            m.file( name, hash.encode( 'hex' ) + HC.mime_ext_lookup[ mime ], file, { 'Content-Type' : HC.mime_string_lookup[ mime ] } )
            
        
    
    return m.get()
    
'''class CaptchaControl( wx.Panel ):
    
    def __init__( self, parent, captcha_type, default ):
        
        wx.Panel.__init__( self, parent )
        
        self._captcha_key = default
        
        self._captcha_challenge = None
        self._captcha_runs_out = 0
        self._bitmap = wx.Bitmap( 20, 20, 24 )
        
        self._timer = wx.Timer( self, ID_TIMER_CAPTCHA )
        self.Bind( wx.EVT_TIMER, self.TIMEREvent, id = ID_TIMER_CAPTCHA )
        
        self._captcha_box_panel = ClientGUICommon.StaticBox( self, 'recaptcha' )
        
        self._captcha_panel = ClientGUICommon.BufferedWindow( self._captcha_box_panel, size = ( 300, 57 ) )
        
        self._refresh_button = wx.Button( self._captcha_box_panel, label = '' )
        self._refresh_button.Bind( wx.EVT_BUTTON, self.EventRefreshCaptcha )
        self._refresh_button.Disable()
        
        self._captcha_time_left = ClientGUICommon.BetterStaticText( self._captcha_box_panel )
        
        self._captcha_entry = wx.TextCtrl( self._captcha_box_panel, style = wx.TE_PROCESS_ENTER )
        self._captcha_entry.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
        self._ready_button = wx.Button( self._captcha_box_panel, label = '' )
        self._ready_button.Bind( wx.EVT_BUTTON, self.EventReady )
        
        sub_vbox = wx.BoxSizer( wx.VERTICAL )
        
        sub_vbox.Add( self._refresh_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        sub_vbox.Add( self._captcha_time_left, CC.FLAGS_SMALL_INDENT )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._captcha_panel, CC.FLAGS_NONE )
        hbox.Add( sub_vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        hbox2 = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox2.Add( self._captcha_entry, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox2.Add( self._ready_button, CC.FLAGS_VCENTER )
        
        self._captcha_box_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._captcha_box_panel.Add( hbox2, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._captcha_box_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self.Disable()
        
    
    def _DrawEntry( self, entry = None ):
        
        if entry is None:
            
            self._captcha_entry.SetValue( '' )
            self._captcha_entry.Disable()
            
        else: self._captcha_entry.SetValue( entry )
        
    
    def _DrawMain( self, dc ):
        
        if self._captcha_challenge is None:
            
            dc.Clear()
            
            self._refresh_button.SetLabelText( '' )
            self._refresh_button.Disable()
            
            self._captcha_time_left.SetLabelText( '' )
            
        elif self._captcha_challenge == '':
            
            dc.Clear()
            
            event = wx.NotifyEvent( CAPTCHA_FETCH_EVENT_TYPE )
            
            wx.QueueEvent( self.GetEventHandler(), event )
            
            if event.IsAllowed():
                
                self._refresh_button.SetLabelText( 'get captcha' )
                self._refresh_button.Enable()
                
            else:
                
                self._refresh_button.SetLabelText( 'not yet' )
                self._refresh_button.Disable()
                
            
            self._captcha_time_left.SetLabelText( '' )
            
        else:
            
            wx_bmp = self._bitmap.GetWxBitmap()
            
            dc.DrawBitmap( wx_bmp, 0, 0 )
            
            wx_bmp.Destroy()
            
            self._refresh_button.SetLabelText( 'get new captcha' )
            self._refresh_button.Enable()
            
            self._captcha_time_left.SetLabelText( HydrusData.ConvertTimestampToPrettyExpires( self._captcha_runs_out ) )
            
        
        del dc
        
    
    def _DrawReady( self, ready = None ):
        
        if ready is None:
            
            self._ready_button.SetLabelText( '' )
            self._ready_button.Disable()
            
        else:
            
            if ready:
                
                self._captcha_entry.Disable()
                self._ready_button.SetLabelText( 'edit' )
                
            else:
                
                self._captcha_entry.Enable()
                self._ready_button.SetLabelText( 'ready' )
                
            
            self._ready_button.Enable()
            
        
    
    def Disable( self ):
        
        self._captcha_challenge = None
        self._captcha_runs_out = 0
        self._bitmap = wx.Bitmap( 20, 20, 24 )
        
        self._DrawMain()
        self._DrawEntry()
        self._DrawReady()
        
        self._timer.Stop()
        
    
    def Enable( self ):
        
        self._captcha_challenge = ''
        self._captcha_runs_out = 0
        self._bitmap = wx.Bitmap( 20, 20, 24 )
        
        self._DrawMain()
        self._DrawEntry()
        self._DrawReady()
        
        self._timer.Start( 1000, wx.TIMER_CONTINUOUS )
        
    
    def EnableWithValues( self, challenge, bitmap, captcha_runs_out, entry, ready ):
        
        if HydrusData.TimeHasPassed( captcha_runs_out ): self.Enable()
        else:
            
            self._captcha_challenge = challenge
            self._captcha_runs_out = captcha_runs_out
            self._bitmap = bitmap
            
            self._DrawMain()
            self._DrawEntry( entry )
            self._DrawReady( ready )
            
            self._timer.Start( 1000, wx.TIMER_CONTINUOUS )
            
        
    
    def EventKeyDown( self, event ):
        
        ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
        
        if key in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ): self.EventReady( None )
        else: event.Skip()
        
    
    def EventReady( self, event ): self._DrawReady( not self._ready_button.GetLabelText() == 'edit' )
    
    def EventRefreshCaptcha( self, event ):
        
        javascript_string = self._controller.DoHTTP( HC.GET, 'https://www.google.com/recaptcha/api/challenge?k=' + self._captcha_key )
        
        ( trash, rest ) = javascript_string.split( 'challenge : \'', 1 )
        
        ( self._captcha_challenge, trash ) = rest.split( '\'', 1 )
        
        jpeg = self._controller.DoHTTP( HC.GET, 'https://www.google.com/recaptcha/api/image?c=' + self._captcha_challenge )
        
        ( os_file_handle, temp_path ) = ClientPaths.GetTempPath()
        
        try:
            
            with open( temp_path, 'wb' ) as f: f.write( jpeg )
            
            self._bitmap = ClientRendering.GenerateHydrusBitmap( temp_path, HC.IMAGE_JPEG )
            
        finally:
            
            HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
            
        
        self._captcha_runs_out = HydrusData.GetNow() + 5 * 60 - 15
        
        self._DrawMain()
        self._DrawEntry( '' )
        self._DrawReady( False )
        
        self._timer.Start( 1000, wx.TIMER_CONTINUOUS )
        
    
    # change this to hold (current challenge, bmp, timestamp it runs out, value, whethere ready to post)
    def GetValues( self ): return ( self._captcha_challenge, self._bitmap, self._captcha_runs_out, self._captcha_entry.GetValue(), self._ready_button.GetLabelText() == 'edit' )
    
    def TIMEREvent( self, event ):
        
        try:
            
            if HydrusData.TimeHasPassed( self._captcha_runs_out ):
                
                self.Enable()
                
            else:
                
                self._DrawMain()
                
            
        except:
            
            self._timer.Stop()
            
            raise
            
        
    '''

'''class Comment( wx.Panel ):
    
    def __init__( self, parent ):
        
        wx.Panel.__init__( self, parent )
        
        self._initial_comment = ''
        
        self._comment_panel = ClientGUICommon.StaticBox( self, 'comment' )
        
        self._comment = ClientGUICommon.SaneMultilineTextCtrl( self._comment_panel, style = wx.TE_READONLY )
        
        self._comment_append = ClientGUICommon.SaneMultilineTextCtrl( self._comment_panel, style = wx.TE_PROCESS_ENTER )
        self._comment_append.Bind( wx.EVT_KEY_UP, self.EventKeyDown )
        
        self._comment_panel.Add( self._comment, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._comment_panel.Add( self._comment_append, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._comment_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def _SetComment( self ):
        
        append = self._comment_append.GetValue()
        
        if self._initial_comment != '' and append != '': comment = self._initial_comment + os.linesep * 2 + append
        else: comment = self._initial_comment + append
        
        self._comment.SetValue( comment )
        
    
    def Disable( self ):
        
        self._initial_comment = ''
        
        self._comment_append.SetValue( '' )
        self._comment_append.Disable()
        
        self._SetComment()
        
    
    def EnableWithValues( self, initial, append ):
        
        self._initial_comment = initial
        
        self._comment_append.SetValue( append )
        self._comment_append.Enable()
        
        self._SetComment()
        
    
    def GetValues( self ): return ( self._initial_comment, self._comment_append.GetValue() )
    
    def EventKeyDown( self, event ):
        
        self._SetComment()
        
        event.Skip()
        
    '''
class ManagementController( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_MANAGEMENT_CONTROLLER
    SERIALISABLE_NAME = 'Client Page Management Controller'
    SERIALISABLE_VERSION = 5
    
    def __init__( self, page_name = 'page' ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._page_name = page_name
        
        self._management_type = None
        
        self._keys = {}
        self._simples = {}
        self._serialisables = {}
        
    
    def __repr__( self ):
        
        return HydrusData.ToByteString( 'Management Controller: ' + self._management_type + ' - ' + self._page_name )
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_keys = { name : value.encode( 'hex' ) for ( name, value ) in self._keys.items() }
        
        serialisable_simples = dict( self._simples )
        
        serialisable_serialisables = { name : value.GetSerialisableTuple() for ( name, value ) in self._serialisables.items() }
        
        return ( self._page_name, self._management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
        
    
    def _InitialiseDefaults( self ):
        
        self._serialisables[ 'media_sort' ] = ClientMedia.MediaSort( ( 'system', CC.SORT_FILES_BY_FILESIZE ), CC.SORT_ASC )
        
        if self._management_type == MANAGEMENT_TYPE_DUPLICATE_FILTER:
            
            self._keys[ 'duplicate_filter_file_domain' ] = CC.LOCAL_FILE_SERVICE_KEY
            
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._page_name, self._management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = serialisable_info
        
        self._InitialiseDefaults()
        
        self._keys.update( { name : key.decode( 'hex' ) for ( name, key ) in serialisable_keys.items() } )
        
        if 'file_service' in self._keys:
            
            if not HG.client_controller.services_manager.ServiceExists( self._keys[ 'file_service' ] ):
                
                self._keys[ 'file_service' ] = CC.COMBINED_LOCAL_FILE_SERVICE_KEY
                
            
        
        self._simples.update( dict( serialisable_simples ) )
        
        self._serialisables.update( { name : HydrusSerialisable.CreateFromSerialisableTuple( value ) for ( name, value ) in serialisable_serialisables.items() } )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            if management_type == MANAGEMENT_TYPE_IMPORT_HDD:
                
                advanced_import_options = serialisable_simples[ 'advanced_import_options' ]
                paths_info = serialisable_simples[ 'paths_info' ]
                paths_to_tags = serialisable_simples[ 'paths_to_tags' ]
                delete_after_success = serialisable_simples[ 'delete_after_success' ]
                
                paths = [ path_info for ( path_type, path_info ) in paths_info if path_type != 'zip' ]
                
                exclude_deleted = advanced_import_options[ 'exclude_deleted' ]
                allow_decompression_bombs = False
                min_size = advanced_import_options[ 'min_size' ]
                max_size = None
                max_gif_size = None
                min_resolution = advanced_import_options[ 'min_resolution' ]
                max_resolution = None
                
                automatic_archive = advanced_import_options[ 'automatic_archive' ]
                
                file_import_options = ClientImportOptions.FileImportOptions()
                
                file_import_options.SetPreImportOptions( exclude_deleted, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution )
                file_import_options.SetPostImportOptions( automatic_archive )
                
                paths_to_tags = { path : { service_key.decode( 'hex' ) : tags for ( service_key, tags ) in service_keys_to_tags } for ( path, service_keys_to_tags ) in paths_to_tags.items() }
                
                hdd_import = ClientImporting.HDDImport( paths = paths, file_import_options = file_import_options, paths_to_tags = paths_to_tags, delete_after_success = delete_after_success )
                
                serialisable_serialisables[ 'hdd_import' ] = hdd_import.GetSerialisableTuple()
                
                del serialisable_serialisables[ 'advanced_import_options' ]
                del serialisable_serialisables[ 'paths_info' ]
                del serialisable_serialisables[ 'paths_to_tags' ]
                del serialisable_serialisables[ 'delete_after_success' ]
                
            
            new_serialisable_info = ( management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            page_name = 'page'
            
            new_serialisable_info = ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            if 'page_of_images_import' in serialisable_serialisables:
                
                serialisable_serialisables[ 'simple_downloader_import' ] = serialisable_serialisables[ 'page_of_images_import' ]
                
                del serialisable_serialisables[ 'page_of_images_import' ]
                
            
            new_serialisable_info = ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 4, new_serialisable_info )
            
        
        if version == 4:
            
            ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            if 'thread_watcher_import' in serialisable_serialisables:
                
                serialisable_serialisables[ 'watcher_import' ] = serialisable_serialisables[ 'thread_watcher_import' ]
                
                del serialisable_serialisables[ 'thread_watcher_import' ]
                
            
            new_serialisable_info = ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 5, new_serialisable_info )
            
        
    
    def GetKey( self, name ):
        
        return self._keys[ name ]
        
    
    def GetPageName( self ):
        
        return self._page_name
        
    
    def GetType( self ):
        
        return self._management_type
        
    
    def GetValueRange( self ):
        
        try:
            
            if self._management_type == MANAGEMENT_TYPE_IMPORT_GALLERY:
                
                gallery_import = self._serialisables[ 'gallery_import' ]
                
                return gallery_import.GetValueRange()
                
            elif self._management_type == MANAGEMENT_TYPE_IMPORT_HDD:
                
                hdd_import = self._serialisables[ 'hdd_import' ]
                
                return hdd_import.GetValueRange()
                
            elif self._management_type == MANAGEMENT_TYPE_IMPORT_SIMPLE_DOWNLOADER:
                
                simple_downloader_import = self._serialisables[ 'simple_downloader_import' ]
                
                return simple_downloader_import.GetValueRange()
                
            elif self._management_type == MANAGEMENT_TYPE_IMPORT_MULTIPLE_WATCHER:
                
                multiple_watcher_import = self._serialisables[ 'multiple_watcher_import' ]
                
                return multiple_watcher_import.GetValueRange()
                
            elif self._management_type == MANAGEMENT_TYPE_IMPORT_WATCHER:
                
                watcher_import = self._serialisables[ 'watcher_import' ]
                
                return watcher_import.GetValueRange()
                
            elif self._management_type == MANAGEMENT_TYPE_IMPORT_URLS:
                
                urls_import = self._serialisables[ 'urls_import' ]
                
                return urls_import.GetValueRange()
                
            
        except KeyError:
            
            return ( 0 , 0 )
            
        
        return ( 0, 0 )
        
    
    def GetVariable( self, name ):
        
        if name in self._simples:
            
            return self._simples[ name ]
            
        else:
            
            return self._serialisables[ name ]
            
        
    
    def HasVariable( self, name ):
        
        return name in self._simples or name in self._serialisables
        
    
    def IsDeadWatcher( self ):
        
        if self._management_type == MANAGEMENT_TYPE_IMPORT_WATCHER:
            
            watcher_import = self.GetVariable( 'watcher_import' )
            
            return watcher_import.IsDead()
            
        
        return False
        
    
    def IsImporter( self ):
        
        return self._management_type in ( MANAGEMENT_TYPE_IMPORT_GALLERY, MANAGEMENT_TYPE_IMPORT_HDD, MANAGEMENT_TYPE_IMPORT_SIMPLE_DOWNLOADER, MANAGEMENT_TYPE_IMPORT_WATCHER, MANAGEMENT_TYPE_IMPORT_MULTIPLE_WATCHER, MANAGEMENT_TYPE_IMPORT_URLS )
        
    
    def SetKey( self, name, key ):
        
        self._keys[ name ] = key
        
    
    def SetPageName( self, name ):
        
        self._page_name = name
        
    
    def SetType( self, management_type ):
        
        self._management_type = management_type
        
        self._InitialiseDefaults()
        
    
    def SetVariable( self, name, value ):
        
        if isinstance( value, HydrusSerialisable.SerialisableBase ):
            
            self._serialisables[ name ] = value
            
        else:
            
            self._simples[ name ] = value
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_MANAGEMENT_CONTROLLER ] = ManagementController

class ManagementPanel( wx.lib.scrolledpanel.ScrolledPanel ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        wx.lib.scrolledpanel.ScrolledPanel.__init__( self, parent, style = wx.BORDER_NONE | wx.VSCROLL )
        
        self.SetupScrolling()
        
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._controller = controller
        self._management_controller = management_controller
        
        self._page = page
        self._page_key = self._management_controller.GetKey( 'page' )
        
        self._sort_by = ClientGUICommon.ChoiceSort( self, management_controller = self._management_controller )
        
        self._collect_by = ClientGUICommon.CheckboxCollect( self, self._page_key )
        
    
    def _MakeCurrentSelectionTagsBox( self, sizer ):
        
        tags_box = ClientGUICommon.StaticBoxSorterForListBoxTags( self, 'selection tags' )
        
        t = ClientGUIListBoxes.ListBoxTagsSelectionManagementPanel( tags_box, self._page_key )
        
        tags_box.SetTagsBox( t )
        
        sizer.Add( tags_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        
    
    def CheckAbleToClose( self ):
        
        pass
        
    
    def CleanBeforeDestroy( self ):
        
        pass
        
    
    def PageHidden( self ):
        
        pass
        
    
    def PageShown( self ):
        
        pass
        
    
    def SetSearchFocus( self ):
        
        pass
        
    
    def Start( self ):
        
        pass
        
    
    def REPEATINGPageUpdate( self ):
        
        pass


class ManagementPanelAutoTag( ManagementPanel ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanel.__init__( self, parent, page, controller, management_controller )
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'auto_tagging.html' ) )
        
        menu_items.append( ( 'normal', 'show some simpler help here', 'Throw up a message box with some simple help.', self._ShowSimpleHelp ) )
        menu_items.append( ( 'normal', 'open the html duplicates help', 'Open the help page for automatic tagging in your web browesr.', page_func ) )
        
        self._help_button = ClientGUICommon.MenuBitmapButton( self, CC.GlobalBMPs.help, menu_items )
        
        self._load_model_panel = ClientGUICommon.StaticBox( self, '1 - load model' )

        self._choose_tagger = wx.DirPickerCtrl( self._load_model_panel, message = "choose tagger", style = wx.DIRP_USE_TEXTCTRL )
        self._choose_tagger.Bind( wx.EVT_DIRPICKER_CHANGED, self._ChooseTaggerChanged )
        # Also potentially a spinny loading progress wheel while it calls load()
        
        #
        
        self._parameter_panel = ClientGUICommon.StaticBox( self, '2 - parameters' )

        self._threshold_slider = wx.Slider( self._parameter_panel, minValue = 0, maxValue = 1000, style = wx.SL_HORIZONTAL )
        self._threshold_slider.Bind( wx.EVT_SLIDER, self._ThresholdChanged )

        self._threshold_spinctrl = wx.SpinCtrlDouble( self._parameter_panel, min = 0, max = 1, inc=0.01, size = ( 50, -1 ) )
        self._threshold_spinctrl.Bind( wx.EVT_SPINCTRLDOUBLE, self._ThresholdChanged )
        
        self._batch_size_spinctrl = wx.SpinCtrl( self._parameter_panel, min = 1, max = 1000, size = ( 50, -1 ) )
        self._batch_size_spinctrl.Bind( wx.EVT_SPINCTRL, self._BatchSizeChanged )
        
        #
        
        self._run_panel = ClientGUICommon.StaticBox( self, '3 - run' )
        
        self._run_button = ClientGUICommon.BetterButton( self._run_panel, 'run tagging', self._RunTagging )

        self._run_gauge = wx.Gauge( self._run_panel )

        #
        
        self._commit_panel = ClientGUICommon.StaticBox( self, '4 - commit' )
        
        self._commit_selected_button = ClientGUICommon.BetterButton( self._commit_panel, 'accept selected', self._CommitSelected)
        self._commit_all_button = ClientGUICommon.BetterButton( self._commit_panel, 'accept all', self._CommitAll )
        
        #
        
        new_options = self._controller.new_options

        self._tagger_path = None
        self._threshold = 0
        self._batch_size = 1

        # self._choose_tagger.SetPath(self._tagger_path)
        self._threshold_slider.SetValue(int(self._threshold * 1000))
        self._threshold_spinctrl.SetValue(self._threshold)

        self._batch_size_spinctrl.SetValue(self._batch_size)

        self._run_gauge.SetValue(0)
        
        #
        
        self._sort_by.Hide()
        self._collect_by.Hide()
        
        gridbox_1 = wx.FlexGridSizer( 1 )

        gridbox_1.Add( self._choose_tagger, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._load_model_panel.Add( gridbox_1, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        gridbox_2 = wx.FlexGridSizer( 3 )
        
        gridbox_2.AddGrowableCol( 1, 1 )
        
        gridbox_2.Add( ClientGUICommon.BetterStaticText( self._parameter_panel, label = 'threshold' ), CC.FLAGS_VCENTER )
        gridbox_2.Add( self._threshold_slider, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        gridbox_2.Add( self._threshold_spinctrl, CC.FLAGS_VCENTER )
        gridbox_2.Add( ClientGUICommon.BetterStaticText( self._parameter_panel, label = 'batch size' ), CC.FLAGS_VCENTER )
        gridbox_2.Add( ( 10, 10 ), CC.FLAGS_EXPAND_PERPENDICULAR )
        gridbox_2.Add( self._batch_size_spinctrl, CC.FLAGS_VCENTER )

        self._parameter_panel.Add( gridbox_2, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )

        #

        self._run_panel.Add( self._run_button, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._run_panel.Add( self._run_gauge, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #

        hbox_commit = wx.BoxSizer( wx.HORIZONTAL )

        hbox_commit.Add( self._commit_selected_button, CC.FLAGS_VCENTER )
        hbox_commit.Add( self._commit_all_button, CC.FLAGS_VCENTER )

        self._commit_panel.Add( hbox_commit, CC.FLAGS_EXPAND_PERPENDICULAR )

        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._load_model_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._parameter_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._run_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._commit_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )

        # 

        # Here: sub to events?
        
    
    def _ShowSimpleHelp( self ):
        message = os.linesep.join([
            'This page will allow a program to automatically assign tags to your files.',
            '',
            '',
            'Before you run it, you\'ll need to download a tagger.',
            '',
            'The default illust2vec neural network tagger can be found at <url>',
            '',
            'I don\'t know what to write here. I\ll doc it out later. #TODO'
        ])
        
        wx.MessageBox( message )


    def _ChooseTaggerChanged( self, evt ):
        if evt.EventType == wx.wxEVT_DIRPICKER_CHANGED:
            self._tagger_path = evt.GetPath()

    
    def _ThresholdChanged( self, evt ):
        if evt.EventType == wx.wxEVT_SLIDER:
            self._threshold = (1.0 * evt.GetInt()) / 1000

        elif evt.EventType == wx.wxEVT_SPINCTRLDOUBLE:
            self._threshold = evt.GetValue()

        if self._threshold_slider.GetValue() != int(self._threshold * 1000):
            self._threshold_slider.SetValue(int(self._threshold * 1000))

        if self._threshold_spinctrl.GetValue() != self._threshold:
            self._threshold_spinctrl.SetValue(self._threshold)


    def _BatchSizeChanged( self, evt ):
        if evt.EventType == wx.wxEVT_SPINCTRL:
            self._batch_size = evt.GetInt()


    def _RunTagging( self ):
        hashes = self._page.GetHashes()

        proposed_tags = self._management_controller.GetVariable('proposed_tags')

        for x in range(0, len(hashes), self._batch_size):
            hash_batch = hashes[x:min(x + self._batch_size, len(hashes))]
            # Should this be a Read?
            tag_batch = self._controller.WriteSynchronous('auto_tag_images', hash_batch, self._tagger_path, self._threshold)
            proposed_tags.update(tag_batch)

        self._management_controller.SetVariable('proposed_tags', proposed_tags)


    def _CommitSelected( self ):
        with ClientGUIDialogs.DialogYesNo( self, 'Stub!' ) as dlg:
            pass


    def _CommitAll( self ):

        proposed_tags = self._management_controller.GetVariable('proposed_tags')

        service_key = CC.LOCAL_TAG_SERVICE_KEY

        content_updates = {service_key: []}

        media = self._page.GetMedia()

        for m in media:

            import code
            code.interact(local=locals())

            hash = m.GetHash()

            tag_manager = m.GetTagsManager()

            new_tags = proposed_tags.get(hash, [])

            for tag in new_tags:
                content_update = HydrusData.ContentUpdate(HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, (tag, {hash}))
                content_updates[service_key].append(content_update)

        self._controller.Write('content_updates', content_updates)

    
management_panel_types_to_classes[ MANAGEMENT_TYPE_AUTO_TAGGING ] = ManagementPanelAutoTag
        
    
class ManagementPanelDuplicateFilter( ManagementPanel ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanel.__init__( self, parent, page, controller, management_controller )
        
        self._job = None
        self._job_key = None
        self._in_break = False
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'refresh', 'This panel does not update itself when files are added or deleted elsewhere in the client. Hitting this will refresh the numbers from the database.', self._RefreshAndUpdateStatus ) )
        menu_items.append( ( 'normal', 'reset potential duplicates', 'This will delete all the potential duplicate pairs found so far and reset their files\' search status.', self._ResetUnknown ) )
        menu_items.append( ( 'separator', 0, 0, 0 ) )
        
        check_manager = ClientGUICommon.CheckboxManagerOptions( 'maintain_similar_files_duplicate_pairs_during_idle' )
        
        menu_items.append( ( 'check', 'search for duplicate pairs at the current distance during normal db maintenance', 'Tell the client to find duplicate pairs in its normal db maintenance cycles, whether you have that set to idle or shutdown time.', check_manager ) )
        
        self._cog_button = ClientGUICommon.MenuBitmapButton( self, CC.GlobalBMPs.cog, menu_items )
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'duplicates.html' ) )
        
        menu_items.append( ( 'normal', 'show some simpler help here', 'Throw up a message box with some simple help.', self._ShowSimpleHelp ) )
        menu_items.append( ( 'normal', 'open the html duplicates help', 'Open the help page for duplicates processing in your web browesr.', page_func ) )
        
        self._help_button = ClientGUICommon.MenuBitmapButton( self, CC.GlobalBMPs.help, menu_items )
        
        self._preparing_panel = ClientGUICommon.StaticBox( self, '1 - preparation' )
        
        # refresh button that just calls update
        
        self._num_phashes_to_regen = ClientGUICommon.BetterStaticText( self._preparing_panel )
        self._num_branches_to_regen = ClientGUICommon.BetterStaticText( self._preparing_panel )
        
        self._phashes_button = ClientGUICommon.BetterBitmapButton( self._preparing_panel, CC.GlobalBMPs.play, self._RegeneratePhashes )
        self._branches_button = ClientGUICommon.BetterBitmapButton( self._preparing_panel, CC.GlobalBMPs.play, self._RebalanceTree )
        
        #
        
        self._searching_panel = ClientGUICommon.StaticBox( self, '2 - discovery' )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'exact match', 'Search for exact matches.', HydrusData.Call( self._SetSearchDistance, HC.HAMMING_EXACT_MATCH ) ) )
        menu_items.append( ( 'normal', 'very similar', 'Search for very similar files.', HydrusData.Call( self._SetSearchDistance, HC.HAMMING_VERY_SIMILAR ) ) )
        menu_items.append( ( 'normal', 'similar', 'Search for similar files.', HydrusData.Call( self._SetSearchDistance, HC.HAMMING_SIMILAR ) ) )
        menu_items.append( ( 'normal', 'speculative', 'Search for files that are probably similar.', HydrusData.Call( self._SetSearchDistance, HC.HAMMING_SPECULATIVE ) ) )
        
        self._search_distance_button = ClientGUICommon.MenuButton( self._searching_panel, 'similarity', menu_items )
        
        self._search_distance_spinctrl = wx.SpinCtrl( self._searching_panel, min = 0, max = 64, size = ( 50, -1 ) )
        self._search_distance_spinctrl.Bind( wx.EVT_SPINCTRL, self.EventSearchDistanceChanged )
        
        self._num_searched = ClientGUICommon.TextAndGauge( self._searching_panel )
        
        self._search_button = ClientGUICommon.BetterBitmapButton( self._searching_panel, CC.GlobalBMPs.play, self._SearchForDuplicates )
        
        #
        
        self._filtering_panel = ClientGUICommon.StaticBox( self, '3 - processing' )
        
        self._file_domain_button = ClientGUICommon.BetterButton( self._filtering_panel, 'file domain', self._FileDomainButtonHit )
        self._num_unknown_duplicates = ClientGUICommon.BetterStaticText( self._filtering_panel )
        self._num_better_duplicates = ClientGUICommon.BetterStaticText( self._filtering_panel )
        self._num_better_duplicates.SetToolTip( 'If this stays at 0, it is likely because your \'worse\' files are being deleted and so are leaving this file domain!' )
        self._num_same_quality_duplicates = ClientGUICommon.BetterStaticText( self._filtering_panel )
        self._num_alternate_duplicates = ClientGUICommon.BetterStaticText( self._filtering_panel )
        self._launch_filter = ClientGUICommon.BetterButton( self._filtering_panel, 'launch the filter', self._LaunchFilter )
        
        random_filtering_panel = ClientGUICommon.StaticBox( self._filtering_panel, 'quick and dirty filtering' )
        
        self._show_some_dupes = ClientGUICommon.BetterButton( random_filtering_panel, 'show some random potential pairs', self._ShowSomeDupes )
        self._set_random_as_alternates_button = ClientGUICommon.BetterButton( random_filtering_panel, 'set current media as all alternates', self._SetCurrentMediaAs, HC.DUPLICATE_ALTERNATE )
        self._set_random_as_same_quality_button = ClientGUICommon.BetterButton( random_filtering_panel, 'set current media as all same quality', self._SetCurrentMediaAs, HC.DUPLICATE_SAME_QUALITY )
        self._set_random_as_not_duplicates_button = ClientGUICommon.BetterButton( random_filtering_panel, 'set current media as not duplicates', self._SetCurrentMediaAs, HC.DUPLICATE_NOT_DUPLICATE )
        
        #
        
        new_options = self._controller.new_options
        
        self._search_distance_spinctrl.SetValue( new_options.GetInteger( 'similar_files_duplicate_pairs_search_distance' ) )
        
        duplicate_filter_file_domain = management_controller.GetKey( 'duplicate_filter_file_domain' )
        
        wx.CallAfter( self._SetFileDomain, duplicate_filter_file_domain ) # this spawns a refreshandupdatestatus
        
        #
        
        self._sort_by.Hide()
        self._collect_by.Hide()
        
        gridbox_1 = wx.FlexGridSizer( 3 )
        
        gridbox_1.AddGrowableCol( 0, 1 )
        
        gridbox_1.Add( self._num_phashes_to_regen, CC.FLAGS_VCENTER )
        gridbox_1.Add( ( 10, 10 ), CC.FLAGS_EXPAND_PERPENDICULAR )
        gridbox_1.Add( self._phashes_button, CC.FLAGS_VCENTER )
        gridbox_1.Add( self._num_branches_to_regen, CC.FLAGS_VCENTER )
        gridbox_1.Add( ( 10, 10 ), CC.FLAGS_EXPAND_PERPENDICULAR )
        gridbox_1.Add( self._branches_button, CC.FLAGS_VCENTER )
        
        self._preparing_panel.Add( gridbox_1, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        distance_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        distance_hbox.Add( ClientGUICommon.BetterStaticText( self._searching_panel, label = 'search distance: ' ), CC.FLAGS_VCENTER )
        distance_hbox.Add( self._search_distance_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        distance_hbox.Add( self._search_distance_spinctrl, CC.FLAGS_VCENTER )
        
        gridbox_2 = wx.FlexGridSizer( 2 )
        
        gridbox_2.AddGrowableCol( 0, 1 )
        
        gridbox_2.Add( self._num_searched, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        gridbox_2.Add( self._search_button, CC.FLAGS_VCENTER )
        
        self._searching_panel.Add( distance_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._searching_panel.Add( gridbox_2, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        random_filtering_panel.Add( self._show_some_dupes, CC.FLAGS_EXPAND_PERPENDICULAR )
        random_filtering_panel.Add( self._set_random_as_alternates_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        random_filtering_panel.Add( self._set_random_as_same_quality_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        random_filtering_panel.Add( self._set_random_as_not_duplicates_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._filtering_panel.Add( self._file_domain_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._filtering_panel.Add( self._num_unknown_duplicates, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._filtering_panel.Add( self._num_better_duplicates, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._filtering_panel.Add( self._num_same_quality_duplicates, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._filtering_panel.Add( self._num_alternate_duplicates, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._filtering_panel.Add( self._launch_filter, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._filtering_panel.Add( random_filtering_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._cog_button, CC.FLAGS_VCENTER )
        hbox.Add( self._help_button, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( hbox, CC.FLAGS_BUTTON_SIZER )
        vbox.Add( self._preparing_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._searching_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._filtering_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        HG.client_controller.sub( self, 'RefreshAndUpdateStatus', 'refresh_dupe_numbers' )
        
    
    def _FileDomainButtonHit( self ):
        
        services_manager = HG.client_controller.services_manager
        
        services = []
        
        services.append( services_manager.GetService( CC.LOCAL_FILE_SERVICE_KEY ) )
        services.append( services_manager.GetService( CC.TRASH_SERVICE_KEY ) )
        services.append( services_manager.GetService( CC.COMBINED_LOCAL_FILE_SERVICE_KEY ) )
        
        menu = wx.Menu()
        
        for service in services:
            
            call = HydrusData.Call( self._SetFileDomain, service.GetServiceKey() )
            
            ClientGUIMenus.AppendMenuItem( self, menu, service.GetName(), 'Set the filtering file domain.', call )
            
        
        HG.client_controller.PopupMenu( self._file_domain_button, menu )
        
    
    def _LaunchFilter( self ):
        
        duplicate_filter_file_domain = self._management_controller.GetKey( 'duplicate_filter_file_domain' )
        
        canvas_frame = ClientGUICanvas.CanvasFrame( self.GetTopLevelParent() )
        
        canvas_window = ClientGUICanvas.CanvasFilterDuplicates( canvas_frame, duplicate_filter_file_domain )
        
        canvas_frame.SetCanvas( canvas_window )
        
    
    def _RebalanceTree( self ):
        
        job_key = ClientThreading.JobKey( cancellable = True )
        
        self._controller.Write( 'maintain_similar_files_tree', job_key = job_key )
        
        self._controller.pub( 'modal_message', job_key )
        
        self._controller.CallToThread( self._THREADWaitOnJob, job_key )
        
    
    def _RefreshAndUpdateStatus( self ):
        
        duplicate_filter_file_domain = self._management_controller.GetKey( 'duplicate_filter_file_domain' )
        
        self._similar_files_maintenance_status = self._controller.Read( 'similar_files_maintenance_status', duplicate_filter_file_domain )
        
        self._UpdateStatus()
        
    
    def _RegeneratePhashes( self ):
        
        job_key = ClientThreading.JobKey( cancellable = True )
        
        self._controller.Write( 'maintain_similar_files_phashes', job_key = job_key )
        
        self._controller.pub( 'modal_message', job_key )
        
        self._controller.CallToThread( self._THREADWaitOnJob, job_key )
        
    
    def _ResetUnknown( self ):
        
        text = 'This will delete all the potential duplicate pairs and reset their files\' search status.'
        text += os.linesep * 2
        text += 'This can be useful if you have accidentally searched too broadly and are now swamped with too many false positives.'
        
        with ClientGUIDialogs.DialogYesNo( self, text ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._controller.Write( 'delete_unknown_duplicate_pairs' )
                
                self._RefreshAndUpdateStatus()
            
        
    
    def _SearchForDuplicates( self ):
        
        job_key = ClientThreading.JobKey( cancellable = True )
        
        search_distance = self._search_distance_spinctrl.GetValue()
        
        self._controller.Write( 'maintain_similar_files_duplicate_pairs', search_distance, job_key = job_key )
        
        self._controller.pub( 'modal_message', job_key )
        
        self._controller.CallToThread( self._THREADWaitOnJob, job_key )
        
    
    def _SetCurrentMediaAs( self, duplicate_type ):
        
        media_panel = self._page.GetMediaPanel()
        
        change_made = media_panel.SetDuplicateStatusForAll( duplicate_type )
        
        if change_made:
            
            self._RefreshAndUpdateStatus()
            
            self._ShowSomeDupes()
            
        
    
    def _SetFileDomain( self, service_key ):
        
        self._management_controller.SetKey( 'duplicate_filter_file_domain', service_key )
        
        services_manager = HG.client_controller.services_manager
        
        service = services_manager.GetService( service_key )
        
        self._file_domain_button.SetLabelText( service.GetName() )
        
        self._RefreshAndUpdateStatus()
        
    
    def _SetSearchDistance( self, value ):
        
        self._search_distance_spinctrl.SetValue( value )
        
        self._UpdateStatus()
        
    
    def _ShowSimpleHelp( self ):
        
        message = 'This page helps you discover and manage files that are very similar to each other. Sometimes these files will be exactly the same--but perhaps have a different resolution or image quality--or they may be recolours or have other small alterations. Here you can quickly define these relationships and hence merge your tags and ratings and, if you wish, delete the \'bad\' files.'
        message += os.linesep * 2
        message += 'There are three steps to this page:'
        message += os.linesep * 2
        message += '1 - Preparing the database for the CPU-heavy job of searching for duplicates.'
        message += os.linesep
        message += '2 - Performing the search and saving the results.'
        message += os.linesep
        message += '3 - Walking through the pairs or groups of potential duplicates and telling the client how they are related.'
        message += os.linesep * 2
        message += 'For the first two steps, you likely just want to click the play buttons and wait for them to complete. They are CPU intensive and lock the client as they work. You can also set them to run in idle time from the cog icon. For the search \'distance\', start at the fast and limited \'exact match\' (0 \'hamming distance\') and slowly expand it as you gain experience with the system.'
        message += os.linesep * 2
        message += 'Once you have found some potential pairs, you can either show some random groups as thumbnails (and process them manually however you prefer), or you can launch the specialised duplicate filter, which lets you quickly assign duplicate status to pairs of files and will automatically merge files and tags between dupes however you prefer.'
        message += os.linesep * 2
        message += 'After launching the duplicate filter, check the keyboard and cog icons on its top hover window. They will let you assign default content merge options (including whether you wish to trash \'bad\' files) and also change the shortcuts for setting the different duplicate statuses. It works like the archive/delete filter, with left-click setting \'this is better\' and right-click setting \'alternates\' by default.'
        message += os.linesep * 2
        message += 'A list of the different duplicate statuses and their meanings will follow this message.'
        
        wx.MessageBox( message )
        
        message = 'The currently supported duplicate statuses are:'
        message += os.linesep * 2
        message += 'potential - This is the default state newly discovered pairs are assigned. They will be loaded in the filter for you to look at.'
        message += os.linesep * 2
        message += 'better/worse - This tells the client that the pair of files are duplicates--but the one you are looking at has better image quality or resolution or lacks an annoying watermark or so on.'
        message += os.linesep * 2
        message += 'same quality - This tells the client that the pair of files are duplicates, and that you cannot discern an obvious quality difference.'
        message += os.linesep * 2
        message += 'alternates - This tells the client that the pair of files are not duplicates but that they are related--perhaps they are a recolour or are an artist\'s different versions of a particular scene. A future version of the client will allow you to further process these alternate groups into family structures and so on.'
        message += os.linesep * 2
        message += 'not duplicates - This tells the client that the discovered pair is a false positive--they are not the same and are not otherwise related. This usually happens when the same part of two files have a similar shape by accident, such as if a hair fringe and a mountain range happen to line up.'
        
        wx.MessageBox( message )
        
    
    def _ShowSomeDupes( self ):
        
        duplicate_filter_file_domain = self._management_controller.GetKey( 'duplicate_filter_file_domain' )
        
        hashes = self._controller.Read( 'duplicate_hashes', duplicate_filter_file_domain, None, HC.DUPLICATE_UNKNOWN )
        
        media_results = self._controller.Read( 'media_results', hashes )
        
        panel = ClientGUIMedia.MediaPanelThumbnails( self._page, self._page_key, CC.COMBINED_LOCAL_FILE_SERVICE_KEY, media_results )
        
        self._page.SwapMediaPanel( panel )
        
    
    def _UpdateStatus( self ):
        
        ( num_phashes_to_regen, num_branches_to_regen, searched_distances_to_count, duplicate_types_to_count ) = self._similar_files_maintenance_status
        
        self._cog_button.Enable()
        
        ClientGUICommon.SetBitmapButtonBitmap( self._phashes_button, CC.GlobalBMPs.play )
        ClientGUICommon.SetBitmapButtonBitmap( self._branches_button, CC.GlobalBMPs.play )
        ClientGUICommon.SetBitmapButtonBitmap( self._search_button, CC.GlobalBMPs.play )
        
        total_num_files = max( num_phashes_to_regen, sum( searched_distances_to_count.values() ) )
        
        if num_phashes_to_regen == 0:
            
            self._num_phashes_to_regen.SetLabelText( 'All ' + HydrusData.ConvertIntToPrettyString( total_num_files ) + ' eligible files up to date!' )
            
            self._phashes_button.Disable()
            
        else:
            
            num_done = total_num_files - num_phashes_to_regen
            
            self._num_phashes_to_regen.SetLabelText( HydrusData.ConvertValueRangeToPrettyString( num_done, total_num_files ) + ' eligible files up to date.' )
            
            self._phashes_button.Enable()
            
        
        if num_branches_to_regen == 0:
            
            self._num_branches_to_regen.SetLabelText( 'Search tree is fast!' )
            
            self._branches_button.Disable()
            
        else:
            
            self._num_branches_to_regen.SetLabelText( HydrusData.ConvertIntToPrettyString( num_branches_to_regen ) + ' search branches to rebalance.' )
            
            self._branches_button.Enable()
            
        
        self._search_distance_button.Enable()
        self._search_distance_spinctrl.Enable()
        
        search_distance = self._search_distance_spinctrl.GetValue()
        
        new_options = self._controller.new_options
        
        new_options.SetInteger( 'similar_files_duplicate_pairs_search_distance', search_distance )
        
        if search_distance in HC.hamming_string_lookup:
            
            button_label = HC.hamming_string_lookup[ search_distance ]
            
        else:
            
            button_label = 'custom'
            
        
        self._search_distance_button.SetLabelText( button_label )
        
        num_searched = sum( ( count for ( value, count ) in searched_distances_to_count.items() if value is not None and value >= search_distance ) )
        
        if num_searched == total_num_files:
            
            self._num_searched.SetValue( 'All potential duplicates found at this distance.', total_num_files, total_num_files )
            
            self._search_button.Disable()
            
        else:
            
            if num_searched == 0:
                
                self._num_searched.SetValue( 'Have not yet searched at this distance.', 0, total_num_files )
                
            else:
                
                self._num_searched.SetValue( 'Searched ' + HydrusData.ConvertValueRangeToPrettyString( num_searched, total_num_files ) + ' files at this distance.', num_searched, total_num_files )
                
            
            self._search_button.Enable()
            
        
        num_unknown = duplicate_types_to_count[ HC.DUPLICATE_UNKNOWN ]
        
        self._num_unknown_duplicates.SetLabelText( HydrusData.ConvertIntToPrettyString( num_unknown ) + ' potential pairs.' )
        self._num_better_duplicates.SetLabelText( HydrusData.ConvertIntToPrettyString( duplicate_types_to_count[ HC.DUPLICATE_BETTER ] ) + ' better/worse pairs.' )
        self._num_same_quality_duplicates.SetLabelText( HydrusData.ConvertIntToPrettyString( duplicate_types_to_count[ HC.DUPLICATE_SAME_QUALITY ] ) + ' same quality pairs.' )
        self._num_alternate_duplicates.SetLabelText( HydrusData.ConvertIntToPrettyString( duplicate_types_to_count[ HC.DUPLICATE_ALTERNATE ] ) + ' alternate pairs.' )
        
        if num_unknown > 0:
            
            self._show_some_dupes.Enable()
            self._launch_filter.Enable()
            
        else:
            
            self._show_some_dupes.Disable()
            self._launch_filter.Disable()
            
        
    
    def _THREADWaitOnJob( self, job_key ):
        
        def wx_done():
            
            if not self:
                
                return
                
            
            self._RefreshAndUpdateStatus()
            
        
        while not job_key.IsDone():
            
            if HydrusThreading.IsThreadShuttingDown():
                
                return
                
            
            time.sleep( 0.25 )
            
        
        wx.CallAfter( wx_done )
        
    
    def EventSearchDistanceChanged( self, event ):
        
        self._UpdateStatus()
        
    
    def RefreshAndUpdateStatus( self ):
        
        self._RefreshAndUpdateStatus()
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_DUPLICATE_FILTER ] = ManagementPanelDuplicateFilter

class ManagementPanelImporter( ManagementPanel ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanel.__init__( self, parent, page, controller, management_controller )
        
        self._controller.sub( self, 'RefreshSort', 'refresh_query' )
        
    
    def _UpdateStatus( self ):
        
        raise NotImplementedError()
        
    
    def PageHidden( self ):
        
        ManagementPanel.PageHidden( self )
        
    
    def PageShown( self ):
        
        ManagementPanel.PageShown( self )
        
        self._UpdateStatus()
        
    
    def RefreshSort( self, page_key ):
        
        if page_key == self._page_key:
            
            self._sort_by.BroadcastSort()
            
        
    
    def REPEATINGPageUpdate( self ):
        
        self._UpdateStatus()
        
    
class ManagementPanelImporterGallery( ManagementPanelImporter ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanelImporter.__init__( self, parent, page, controller, management_controller )
        
        self._gallery_import = self._management_controller.GetVariable( 'gallery_import' )
        
        self._gallery_downloader_panel = ClientGUICommon.StaticBox( self, 'gallery downloader' )
        
        self._import_queue_panel = ClientGUICommon.StaticBox( self._gallery_downloader_panel, 'imports' )
        
        self._current_action = ClientGUICommon.BetterStaticText( self._import_queue_panel )
        self._seed_cache_control = ClientGUISeedCache.SeedCacheStatusControl( self._import_queue_panel, self._controller, self._page_key )
        self._file_download_control = ClientGUIControls.NetworkJobControl( self._import_queue_panel )
        
        self._files_pause_button = wx.BitmapButton( self._import_queue_panel, bitmap = CC.GlobalBMPs.pause )
        self._files_pause_button.Bind( wx.EVT_BUTTON, self.EventFilesPause )
        
        self._gallery_panel = ClientGUICommon.StaticBox( self._gallery_downloader_panel, 'gallery parser' )
        
        self._gallery_status = ClientGUICommon.BetterStaticText( self._gallery_panel )
        
        self._gallery_download_control = ClientGUIControls.NetworkJobControl( self._gallery_panel )
        
        self._gallery_pause_button = wx.BitmapButton( self._gallery_panel, bitmap = CC.GlobalBMPs.pause )
        self._gallery_pause_button.Bind( wx.EVT_BUTTON, self.EventGalleryPause )
        
        self._gallery_cancel_button = wx.BitmapButton( self._gallery_panel, bitmap = CC.GlobalBMPs.stop )
        self._gallery_cancel_button.Bind( wx.EVT_BUTTON, self.EventGalleryCancel )
        
        self._pending_queries_panel = ClientGUICommon.StaticBox( self._gallery_downloader_panel, 'pending queries' )
        
        self._pending_queries_listbox = wx.ListBox( self._pending_queries_panel, size = ( -1, 100 ), style = wx.LB_EXTENDED )
        
        self._advance_button = wx.Button( self._pending_queries_panel, label = u'\u2191' )
        self._advance_button.Bind( wx.EVT_BUTTON, self.EventAdvance )
        
        self._delete_button = wx.Button( self._pending_queries_panel, label = 'X' )
        self._delete_button.Bind( wx.EVT_BUTTON, self.EventDelete )
        
        self._delay_button = wx.Button( self._pending_queries_panel, label = u'\u2193' )
        self._delay_button.Bind( wx.EVT_BUTTON, self.EventDelay )
        
        self._query_input = ClientGUIControls.TextAndPasteCtrl( self._pending_queries_panel, self._PendQueries )
        
        self._file_limit = ClientGUICommon.NoneableSpinCtrl( self._gallery_downloader_panel, 'stop after this many files', min = 1, none_phrase = 'no limit' )
        self._file_limit.Bind( wx.EVT_SPINCTRL, self.EventFileLimit )
        self._file_limit.SetToolTip( 'per query, stop searching the gallery once this many files has been reached' )
        
        self._gallery_import.SetDownloadControls( self._file_download_control, self._gallery_download_control )
        
        ( file_import_options, tag_import_options, file_limit ) = self._gallery_import.GetOptions()
        
        gallery_identifier = self._gallery_import.GetGalleryIdentifier()
        
        ( namespaces, search_value ) = ClientDefaults.GetDefaultNamespacesAndSearchValue( gallery_identifier )
        
        self._file_import_options = ClientGUIImport.FileImportOptionsButton( self._gallery_downloader_panel, file_import_options, self._gallery_import.SetFileImportOptions )
        self._tag_import_options = ClientGUIImport.TagImportOptionsButton( self._gallery_downloader_panel, namespaces, tag_import_options, self._gallery_import.SetTagImportOptions )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._gallery_status, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        hbox.Add( self._gallery_pause_button, CC.FLAGS_VCENTER )
        hbox.Add( self._gallery_cancel_button, CC.FLAGS_VCENTER )
        
        self._gallery_panel.Add( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_panel.Add( self._gallery_download_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        queue_buttons_vbox = wx.BoxSizer( wx.VERTICAL )
        
        queue_buttons_vbox.Add( self._advance_button, CC.FLAGS_VCENTER )
        queue_buttons_vbox.Add( self._delete_button, CC.FLAGS_VCENTER )
        queue_buttons_vbox.Add( self._delay_button, CC.FLAGS_VCENTER )
        
        queue_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        queue_hbox.Add( self._pending_queries_listbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        queue_hbox.Add( queue_buttons_vbox, CC.FLAGS_VCENTER )
        
        self._pending_queries_panel.Add( queue_hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        self._pending_queries_panel.Add( self._query_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._current_action, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        hbox.Add( self._files_pause_button, CC.FLAGS_VCENTER )
        
        self._import_queue_panel.Add( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.Add( self._seed_cache_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.Add( self._file_download_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._gallery_downloader_panel.Add( self._import_queue_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_downloader_panel.Add( self._gallery_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_downloader_panel.Add( self._pending_queries_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._gallery_downloader_panel.Add( self._file_limit, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_downloader_panel.Add( self._file_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_downloader_panel.Add( self._tag_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._sort_by, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._collect_by.Hide()
        
        vbox.Add( self._gallery_downloader_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        #
        
        seed_cache = self._gallery_import.GetSeedCache()
        
        self._seed_cache_control.SetSeedCache( seed_cache )
        
        self._query_input.SetValue( search_value )
        
        self._file_limit.SetValue( file_limit )
        
        self._UpdateStatus()
        
    
    def _PendQueries( self, queries ):
        
        for query in queries:
            
            self._gallery_import.PendQuery( query )
            
        
        self._UpdateStatus()
        
    
    def _SeedCache( self ):
        
        seed_cache = self._gallery_import.GetSeedCache()
        
        title = 'file import status'
        frame_key = 'file_import_status'
        
        frame = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( self, title, frame_key )
        
        panel = ClientGUISeedCache.EditSeedCachePanel( frame, self._controller, seed_cache )
        
        frame.SetPanel( panel )
        
    
    def _UpdateStatus( self ):
        
        ( pending_queries, gallery_status, current_action, files_paused, gallery_paused, gallery_cancellable ) = self._gallery_import.GetStatus()
        
        if self._pending_queries_listbox.GetStrings() != pending_queries:
            
            selected_indices = self._pending_queries_listbox.GetSelections()
            
            selected_strings = [ self._pending_queries_listbox.GetString( i ) for i in selected_indices ]
            
            self._pending_queries_listbox.SetItems( pending_queries )
            
            for selected_string in selected_strings:
                
                selection_index = self._pending_queries_listbox.FindString( selected_string )
                
                if selection_index != wx.NOT_FOUND:
                    
                    self._pending_queries_listbox.Select( selection_index )
                    
                
            
        
        if files_paused:
            
            ClientGUICommon.SetBitmapButtonBitmap( self._files_pause_button, CC.GlobalBMPs.play )
            
        else:
            
            ClientGUICommon.SetBitmapButtonBitmap( self._files_pause_button, CC.GlobalBMPs.pause )
            
        
        if gallery_paused:
            
            ClientGUICommon.SetBitmapButtonBitmap( self._gallery_pause_button, CC.GlobalBMPs.play )
            
        else:
            
            ClientGUICommon.SetBitmapButtonBitmap( self._gallery_pause_button, CC.GlobalBMPs.pause )
            
        
        if gallery_cancellable:
            
            self._gallery_cancel_button.Enable()
            
        else:
            
            self._gallery_cancel_button.Disable()
            
        
        if gallery_paused:
            
            if gallery_status == '':
                
                gallery_status = 'paused'
                
            else:
                
                gallery_status = 'paused - ' + gallery_status
                
            
        
        self._gallery_status.SetLabelText( gallery_status )
        
        if files_paused:
            
            if current_action == '':
                
                current_action = 'paused'
                
            else:
                
                current_action = 'pausing - ' + current_action
                
            
        
        self._current_action.SetLabelText( current_action )
        
    
    def CheckAbleToClose( self ):
        
        if self._gallery_import.CurrentlyWorking():
            
            raise HydrusExceptions.VetoException( 'This page is still importing.' )
            
        
    
    def EventAdvance( self, event ):
        
        selected_indices = self._pending_queries_listbox.GetSelections()
        
        selected_strings = [ self._pending_queries_listbox.GetString( i ) for i in selected_indices ]
        
        if len( selected_strings ) > 0:
            
            self._gallery_import.AdvanceQueries( selected_strings )
            
            self._UpdateStatus()
            
        
    
    def EventDelay( self, event ):
        
        selected_indices = self._pending_queries_listbox.GetSelections()
        
        selected_strings = [ self._pending_queries_listbox.GetString( i ) for i in selected_indices ]
        
        if len( selected_strings ) > 0:
            
            self._gallery_import.DelayQueries( selected_strings )
            
            self._UpdateStatus()
            
        
    
    def EventDelete( self, event ):
        
        selected_indices = self._pending_queries_listbox.GetSelections()
        
        selected_strings = [ self._pending_queries_listbox.GetString( i ) for i in selected_indices ]
        
        if len( selected_strings ) > 0:
            
            self._gallery_import.DeleteQueries( selected_strings )
            
            self._UpdateStatus()
            
        
    
    def EventFileLimit( self, event ):
        
        self._gallery_import.SetFileLimit( self._file_limit.GetValue() )
        
        event.Skip()
        
    
    def EventFilesPause( self, event ):
        
        self._gallery_import.PausePlayFiles()
        
        self._UpdateStatus()
        
    
    def EventGalleryCancel( self, event ):
        
        self._gallery_import.FinishCurrentQuery()
        
        self._UpdateStatus()
        
    
    def EventGalleryPause( self, event ):
        
        self._gallery_import.PausePlayGallery()
        
        self._UpdateStatus()
        
    
    def SetSearchFocus( self ):
        
        wx.CallAfter( self._query_input.SetFocus )
        
    
    def Start( self ):
        
        self._gallery_import.Start( self._page_key )
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_IMPORT_GALLERY ] = ManagementPanelImporterGallery

class ManagementPanelImporterHDD( ManagementPanelImporter ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanelImporter.__init__( self, parent, page, controller, management_controller )
        
        self._import_queue_panel = ClientGUICommon.StaticBox( self, 'import summary' )
        
        self._current_action = ClientGUICommon.BetterStaticText( self._import_queue_panel )
        self._seed_cache_control = ClientGUISeedCache.SeedCacheStatusControl( self._import_queue_panel, self._controller, self._page_key )
        
        self._pause_button = wx.BitmapButton( self._import_queue_panel, bitmap = CC.GlobalBMPs.pause )
        self._pause_button.Bind( wx.EVT_BUTTON, self.EventPause )
        
        self._hdd_import = self._management_controller.GetVariable( 'hdd_import' )
        
        file_import_options = self._hdd_import.GetFileImportOptions()
        
        self._file_import_options = ClientGUIImport.FileImportOptionsButton( self._import_queue_panel, file_import_options, self._hdd_import.SetFileImportOptions )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._sort_by, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._collect_by.Hide()
        
        self._import_queue_panel.Add( self._current_action, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.Add( self._seed_cache_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.Add( self._pause_button, CC.FLAGS_LONE_BUTTON )
        self._import_queue_panel.Add( self._file_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox.Add( self._import_queue_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        #
        
        seed_cache = self._hdd_import.GetSeedCache()
        
        self._seed_cache_control.SetSeedCache( seed_cache )
        
        self._UpdateStatus()
        
    
    def _UpdateStatus( self ):
        
        ( current_action, paused ) = self._hdd_import.GetStatus()
        
        if paused:
            
            ClientGUICommon.SetBitmapButtonBitmap( self._pause_button, CC.GlobalBMPs.play )
            
        else:
            
            ClientGUICommon.SetBitmapButtonBitmap( self._pause_button, CC.GlobalBMPs.pause )
            
        
        if paused:
            
            if current_action == '':
                
                current_action = 'paused'
                
            else:
                
                current_action = 'pausing - ' + current_action
                
            
        
        self._current_action.SetLabelText( current_action )
        
    
    def CheckAbleToClose( self ):
        
        if self._hdd_import.CurrentlyWorking():
            
            raise HydrusExceptions.VetoException( 'This page is still importing.' )
            
        
    
    def EventPause( self, event ):
        
        self._hdd_import.PausePlay()
        
        self._UpdateStatus()
        
    
    def Start( self ):
        
        self._hdd_import.Start( self._page_key )
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_IMPORT_HDD ] = ManagementPanelImporterHDD

class ManagementPanelImporterMultipleWatcher( ManagementPanelImporter ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanelImporter.__init__( self, parent, page, controller, management_controller )
        
        self._last_watcher_keys = set()
        self._next_update_time = 0
        self._highlit_watcher = None
        
        self._multiple_watcher_import = self._management_controller.GetVariable( 'multiple_watcher_import' )
        
        #
        
        self._watchers_panel = ClientGUICommon.StaticBox( self, 'watchers' )
        
        self._watchers_status_st_top = ClientGUICommon.BetterStaticText( self._watchers_panel )
        self._watchers_status_st_bottom = ClientGUICommon.BetterStaticText( self._watchers_panel )
        
        self._watchers_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._watchers_panel )
        
        self._watchers_listctrl = ClientGUIListCtrl.BetterListCtrl( self._watchers_listctrl_panel, 'watchers', 6, 12, [ ( 'subject', -1 ), ( 'status', 8 ), ( 'progress', 15 ) ], self._ConvertDataToListCtrlTuples, delete_key_callback = self._RemoveWatchers, activation_callback = self._HighlightWatcher )
        
        self._watchers_listctrl_panel.SetListCtrl( self._watchers_listctrl )
        
        self._watchers_listctrl_panel.AddButton( 'clear highlight', self._ClearExistingHighlightAndPanel, enabled_check_func = self._CanClearHighlight )
        self._watchers_listctrl_panel.AddButton( 'highlight', self._HighlightWatcher, enabled_check_func = self._CanHighlight )
        
        self._watchers_listctrl_panel.NewButtonRow()
        
        self._watchers_listctrl_panel.AddButton( 'pause/play', self._PausePlay, enabled_only_on_selection = True )
        self._watchers_listctrl_panel.AddButton( 'check now', self._CheckNow, enabled_only_on_selection = True )
        self._watchers_listctrl_panel.AddButton( 'remove', self._RemoveWatchers, enabled_only_on_selection = True )
        
        self._watcher_url_input = ClientGUIControls.TextAndPasteCtrl( self._watchers_panel, self._AddURLs )
        
        self._watchers_listctrl.Sort( 0 )
        
        # suck up watchers from elsewhere in the program (presents a checklistboxdialog)
        
        #
        
        self._watchers_panel.Add( self._watchers_status_st_top, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._watchers_panel.Add( self._watchers_status_st_bottom, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._watchers_panel.Add( self._watchers_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._watchers_panel.Add( self._watcher_url_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._sort_by, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._collect_by.Hide()
        
        vbox.Add( self._watchers_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        #
        
        self._UpdateStatus()
        
        HG.client_controller.sub( self, 'PendURL', 'pend_url' )
        
    
    def _AddURLs( self, urls ):
        
        for url in urls:
            
            self._multiple_watcher_import.AddURL( url )
            
        
    
    def _CanClearHighlight( self ):
        
        return self._highlit_watcher is not None
        
    
    def _CanHighlight( self ):
        
        num_selected = len( self._watchers_listctrl.GetData( only_selected = True ) )
        
        return num_selected == 1
        
    
    def _CheckNow( self ):
        
        for watcher in self._watchers_listctrl.GetData( only_selected = True ):
            
            watcher.CheckNow()
            
        
    
    def _ClearExistingHighlight( self ):
        
        if self._highlit_watcher is not None:
            
            publish_to_page = False
            
            self._highlit_watcher.Repage( self._page_key, publish_to_page )
            
            self._highlit_watcher = None
            
            self._watchers_listctrl_panel.UpdateButtons()
            
        
    
    def _ClearExistingHighlightAndPanel( self ):
        
        self._ClearExistingHighlight()
        
        media_results = []
        
        panel = ClientGUIMedia.MediaPanelThumbnails( self._page, self._page_key, CC.LOCAL_FILE_SERVICE_KEY, media_results )
        
        self._page.SwapMediaPanel( panel )
        
        self._watchers_listctrl.UpdateDatas()
        
    
    def _ConvertDataToListCtrlTuples( self, watcher ):
        
        pretty_subject = watcher.GetSubject()
        
        if watcher == self._highlit_watcher:
            
            pretty_subject = '* ' + pretty_subject
            
        
        status = watcher.GetSimpleStatus()
        
        ( value, range ) = watcher.GetValueRange()
        
        progress = ( range, value )
        
        subject = pretty_subject.lower()
        pretty_status = status
        
        if value == range:
            
            if value == 0:
                
                pretty_progress = 'no files'
                
            else:
                
                pretty_progress = HydrusData.ConvertIntToPrettyString( value )
                
            
        else:
            
            pretty_progress = HydrusData.ConvertValueRangeToPrettyString( value, range )
            
        
        display_tuple = ( pretty_subject, pretty_status, pretty_progress )
        sort_tuple = ( subject, status, progress )
        
        return ( display_tuple, sort_tuple )
        
    
    def _HighlightWatcher( self ):
        
        selected = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( selected ) == 1:
            
            new_highlight = selected[0]
            
            if new_highlight == self._highlit_watcher:
                
                self._ClearExistingHighlightAndPanel()
                
            else:
                
                self._ClearExistingHighlight()
                
                self._highlit_watcher = selected[0]
                
                hashes = self._highlit_watcher.GetPresentedHashes()
                
                media_results = HG.client_controller.Read( 'media_results', hashes )
                
                hashes_to_media_results = { media_result.GetHash() : media_result for media_result in media_results }
                
                sorted_media_results = [ hashes_to_media_results[ hash ] for hash in hashes ]
                
                panel = ClientGUIMedia.MediaPanelThumbnails( self._page, self._page_key, CC.LOCAL_FILE_SERVICE_KEY, sorted_media_results )
                
                self._page.SwapMediaPanel( panel )
                
                publish_to_page = True
                
                self._highlit_watcher.Repage( self._page_key, publish_to_page )
                
                self._watchers_listctrl_panel.UpdateButtons()
                
                self._watchers_listctrl.UpdateDatas()
                
            
        
    
    def _PausePlay( self ):
        
        for watcher in self._watchers_listctrl.GetData( only_selected = True ):
            
            watcher.PausePlay()
            
        
    
    def _RemoveWatchers( self ):
        
        removees = list( self._watchers_listctrl.GetData( only_selected = True ) )
        
        if len( removees ) == 0:
            
            return
            
        
        num_working = 0
        num_alive = 0
        
        for watcher in removees:
            
            if watcher.CurrentlyWorking():
                
                num_working += 1
                
            
            if watcher.CurrentlyAlive():
                
                num_alive += 1
                
            
        
        message = 'Remove the ' + HydrusData.ConvertIntToPrettyString( len( removees ) ) + ' selected watchers?'
        
        if num_working > 0:
            
            message += os.linesep * 2
            message += HydrusData.ConvertIntToPrettyString( num_working ) + ' are still working.'
            
        
        if num_alive > 0:
            
            message += os.linesep * 2
            message += HydrusData.ConvertIntToPrettyString( num_alive ) + ' are not yet DEAD.'
            
        
        if self._highlit_watcher is not None and self._highlit_watcher in removees:
            
            message += os.linesep * 2
            message += 'The currently highlit watcher will be removed, and the media panel cleared.'
            
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                highlight_was_included = False
                
                for watcher in removees:
                    
                    if self._highlit_watcher is not None and watcher == self._highlit_watcher:
                        
                        highlight_was_included = True
                        
                    
                    self._multiple_watcher_import.RemoveWatcher( watcher.GetWatcherKey() )
                    
                
                if highlight_was_included:
                    
                    self._ClearExistingHighlightAndPanel()
                    
                
            
        
    
    def _UpdateStatus( self ):
        
        if HydrusData.TimeHasPassed( self._next_update_time ):
            
            self._next_update_time = HydrusData.GetNow() + 1
            
            #
            
            watcher_keys = self._multiple_watcher_import.GetWatcherKeys()
            
            #
            
            if len( watcher_keys ) == 0:
                
                text_top = 'waiting for new watchers'
                text_bottom = ''
                
            else:
                
                num_dead = self._multiple_watcher_import.GetNumDead()
                
                if num_dead == 0:
                    
                    num_dead_text = ''
                    
                else:
                    
                    num_dead_text = HydrusData.ConvertIntToPrettyString( num_dead ) + ' DEAD - '
                    
                
                ( status, ( value, range ) ) = self._multiple_watcher_import.GetTotalStatus()
                
                text_top = HydrusData.ConvertIntToPrettyString( len( watcher_keys ) ) + ' watchers - ' + num_dead_text + HydrusData.ConvertValueRangeToPrettyString( value, range )
                text_bottom = status
                
            
            self._watchers_status_st_top.SetLabelText( text_top )
            self._watchers_status_st_bottom.SetLabelText( text_bottom )
            
            #
            
            if self._last_watcher_keys == watcher_keys:
                
                sort_data_has_changed = self._watchers_listctrl.UpdateDatas()
                
                if sort_data_has_changed:
                    
                    self._watchers_listctrl.Sort()
                    
                
            else:
                
                self._last_watcher_keys = watcher_keys
                
                watchers = self._multiple_watcher_import.GetWatchers()
                
                self._watchers_listctrl.SetData( watchers )
                
            
        
    
    def CheckAbleToClose( self ):
        
        num_working = 0
        
        for watcher in self._multiple_watcher_import.GetWatchers():
            
            if watcher.CurrentlyWorking():
                
                num_working += 1
                
            
        
        if num_working > 0:
            
            raise HydrusExceptions.VetoException( HydrusData.ConvertIntToPrettyString( num_working ) + ' watchers are still importing.' )
            
        
    
    def PendURL( self, page_key, url ):
        
        if page_key == self._page_key:
            
            self._multiple_watcher_import.AddURL( url )
            
        
    
    def SetSearchFocus( self ):
        
        wx.CallAfter( self._watcher_url_input.SetFocus )
        
    
    def Start( self ):
        
        self._multiple_watcher_import.Start( self._page_key )
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_IMPORT_MULTIPLE_WATCHER ] = ManagementPanelImporterMultipleWatcher

class ManagementPanelImporterSimpleDownloader( ManagementPanelImporter ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanelImporter.__init__( self, parent, page, controller, management_controller )
        
        self._simple_downloader_import = self._management_controller.GetVariable( 'simple_downloader_import' )
        
        #
        
        self._simple_downloader_panel = ClientGUICommon.StaticBox( self, 'simple downloader' )
        
        #
        
        self._import_queue_panel = ClientGUICommon.StaticBox( self._simple_downloader_panel, 'imports' )
        
        self._pause_files_button = wx.BitmapButton( self._import_queue_panel, bitmap = CC.GlobalBMPs.pause )
        self._pause_files_button.Bind( wx.EVT_BUTTON, self.EventPauseFiles )
        
        self._current_action = ClientGUICommon.BetterStaticText( self._import_queue_panel )
        self._seed_cache_control = ClientGUISeedCache.SeedCacheStatusControl( self._import_queue_panel, self._controller, self._page_key )
        self._file_download_control = ClientGUIControls.NetworkJobControl( self._import_queue_panel )
        
        #
        
        self._pending_jobs_panel = ClientGUICommon.StaticBox( self._simple_downloader_panel, 'pending urls' )
        
        self._pause_queue_button = wx.BitmapButton( self._pending_jobs_panel, bitmap = CC.GlobalBMPs.pause )
        self._pause_queue_button.Bind( wx.EVT_BUTTON, self.EventPauseQueue )
        
        self._parser_status = ClientGUICommon.BetterStaticText( self._pending_jobs_panel )
        
        self._page_download_control = ClientGUIControls.NetworkJobControl( self._pending_jobs_panel )
        
        self._pending_jobs_listbox = wx.ListBox( self._pending_jobs_panel, size = ( -1, 100 ) )
        
        self._advance_button = wx.Button( self._pending_jobs_panel, label = u'\u2191' )
        self._advance_button.Bind( wx.EVT_BUTTON, self.EventAdvance )
        
        self._delete_button = wx.Button( self._pending_jobs_panel, label = 'X' )
        self._delete_button.Bind( wx.EVT_BUTTON, self.EventDelete )
        
        self._delay_button = wx.Button( self._pending_jobs_panel, label = u'\u2193' )
        self._delay_button.Bind( wx.EVT_BUTTON, self.EventDelay )
        
        self._page_url_input = ClientGUIControls.TextAndPasteCtrl( self._pending_jobs_panel, self._PendPageURLs )
        
        self._formulae = ClientGUICommon.BetterChoice( self._pending_jobs_panel )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'edit formulae', 'Edit these parsing formulae.', self._EditFormulae ) )
        
        self._formula_cog = ClientGUICommon.MenuBitmapButton( self._pending_jobs_panel, CC.GlobalBMPs.cog, menu_items )
        
        self._RefreshFormulae()
        
        file_import_options = self._simple_downloader_import.GetFileImportOptions()
        
        self._file_import_options = ClientGUIImport.FileImportOptionsButton( self._simple_downloader_panel, file_import_options, self._simple_downloader_import.SetFileImportOptions )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._current_action, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        hbox.Add( self._pause_files_button, CC.FLAGS_VCENTER )
        
        self._import_queue_panel.Add( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.Add( self._seed_cache_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.Add( self._file_download_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        queue_buttons_vbox = wx.BoxSizer( wx.VERTICAL )
        
        queue_buttons_vbox.Add( self._advance_button, CC.FLAGS_VCENTER )
        queue_buttons_vbox.Add( self._delete_button, CC.FLAGS_VCENTER )
        queue_buttons_vbox.Add( self._delay_button, CC.FLAGS_VCENTER )
        
        queue_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        queue_hbox.Add( self._pending_jobs_listbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        queue_hbox.Add( queue_buttons_vbox, CC.FLAGS_VCENTER )
        
        formulae_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        formulae_hbox.Add( self._formulae, CC.FLAGS_EXPAND_BOTH_WAYS )
        formulae_hbox.Add( self._formula_cog, CC.FLAGS_VCENTER )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._parser_status, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        hbox.Add( self._pause_queue_button, CC.FLAGS_VCENTER )
        
        self._pending_jobs_panel.Add( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._pending_jobs_panel.Add( self._page_download_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._pending_jobs_panel.Add( queue_hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        self._pending_jobs_panel.Add( self._page_url_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._pending_jobs_panel.Add( formulae_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        self._simple_downloader_panel.Add( self._import_queue_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._simple_downloader_panel.Add( self._pending_jobs_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._simple_downloader_panel.Add( self._file_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._sort_by, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._collect_by.Hide()
        
        vbox.Add( self._simple_downloader_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        #
        
        self._formulae.Bind( wx.EVT_CHOICE, self.EventFormulaChanged )
        
        seed_cache = self._simple_downloader_import.GetSeedCache()
        
        self._seed_cache_control.SetSeedCache( seed_cache )
        
        self._simple_downloader_import.SetDownloadControlFile( self._file_download_control )
        self._simple_downloader_import.SetDownloadControlPage( self._page_download_control )
        
        self._UpdateStatus()
        
    
    def _EditFormulae( self ):
        
        def data_to_pretty_callable( data ):
            
            simple_downloader_formula = data
            
            return simple_downloader_formula.GetName()
            
        
        def edit_callable( data ):
            
            simple_downloader_formula = data
            
            name = simple_downloader_formula.GetName()
            
            with ClientGUIDialogs.DialogTextEntry( dlg, 'edit name', default = name ) as dlg_2:
                
                if dlg_2.ShowModal() == wx.ID_OK:
                    
                    name = dlg_2.GetValue()
                    
                else:
                    
                    return ( False, None )
                    
                
            
            with ClientGUITopLevelWindows.DialogEdit( dlg, 'edit formula' ) as dlg_3:
                
                panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg_3 )
                
                formula = simple_downloader_formula.GetFormula()
                
                control = ClientGUIParsing.EditFormulaPanel( panel, formula, lambda: ( {}, '' ) )
                
                panel.SetControl( control )
                
                dlg_3.SetPanel( panel )
                
                if dlg_3.ShowModal() == wx.ID_OK:
                    
                    formula = control.GetValue()
                    
                    simple_downloader_formula = ClientParsing.SimpleDownloaderParsingFormula( name = name, formula = formula )
                    
                    return ( True, simple_downloader_formula )
                    
                else:
                    
                    return ( False, None )
                    
                
            
        
        def add_callable():
            
            data = ClientParsing.SimpleDownloaderParsingFormula()
            
            return edit_callable( data )
            
        
        formulae = list( self._controller.new_options.GetSimpleDownloaderFormulae() )
        
        formulae.sort( key = lambda o: o.GetName() )
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit simple downloader formulae' ) as dlg:
            
            panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
            
            height_num_chars = 20
            
            control = ClientGUIListBoxes.AddEditDeleteListBoxUniqueNamedObjects( panel, height_num_chars, data_to_pretty_callable, add_callable, edit_callable )
            
            control.AddSeparator()
            control.AddImportExportButtons( ( ClientParsing.SimpleDownloaderParsingFormula, ) )
            control.AddSeparator()
            control.AddDefaultsButton( ClientDefaults.GetDefaultSimpleDownloaderFormulae )
            
            control.AddDatas( formulae )
            
            panel.SetControl( control )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                formulae = control.GetData()
                
                self._controller.new_options.SetSimpleDownloaderFormulae( formulae )
                
            
        
        self._RefreshFormulae()
        
    
    def _PendPageURLs( self, urls ):
        
        urls = [ url for url in urls if url.startswith( 'http' ) ]
        
        simple_downloader_formula = self._formulae.GetChoice()
        
        for url in urls:
            
            job = ( url, simple_downloader_formula )
            
            self._simple_downloader_import.PendJob( job )
            
        
        self._UpdateStatus()
        
    
    def _RefreshFormulae( self ):
        
        self._formulae.Clear()
        
        to_select = None
        
        select_name = self._simple_downloader_import.GetFormulaName()
        
        simple_downloader_formulae = list( self._controller.new_options.GetSimpleDownloaderFormulae() )
        
        simple_downloader_formulae.sort( key = lambda o: o.GetName() )
        
        for ( i, simple_downloader_formula ) in enumerate( simple_downloader_formulae ):
            
            name = simple_downloader_formula.GetName()
            
            self._formulae.Append( name, simple_downloader_formula )
            
            if name == select_name:
                
                to_select = i
                
            
        
        if to_select is not None:
            
            self._formulae.Select( to_select )
            
        
    
    def _SeedCache( self ):
        
        seed_cache = self._simple_downloader_import.GetSeedCache()
        
        title = 'file import status'
        frame_key = 'file_import_status'
        
        frame = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( self, title, frame_key )
        
        panel = ClientGUISeedCache.EditSeedCachePanel( frame, self._controller, seed_cache )
        
        frame.SetPanel( panel )
        
    
    def _UpdateStatus( self ):
        
        ( pending_jobs, parser_status, current_action, queue_paused, files_paused ) = self._simple_downloader_import.GetStatus()
        
        current_pending_jobs = [ self._pending_jobs_listbox.GetClientData( i ) for i in range( self._pending_jobs_listbox.GetCount() ) ]
        
        if current_pending_jobs != pending_jobs:
            
            selected_string = self._pending_jobs_listbox.GetStringSelection()
            
            self._pending_jobs_listbox.Clear()
            
            for job in pending_jobs:
                
                ( url, simple_downloader_formula ) = job
                
                pretty_job = simple_downloader_formula.GetName() + ': ' + url
                
                self._pending_jobs_listbox.Append( pretty_job, job )
                
            
            selection_index = self._pending_jobs_listbox.FindString( selected_string )
            
            if selection_index != wx.NOT_FOUND:
                
                self._pending_jobs_listbox.Select( selection_index )
                
            
        
        if queue_paused:
            
            parser_status = 'paused'
            
        
        self._parser_status.SetLabelText( parser_status )
        
        if current_action == '' and files_paused:
            
            current_action = 'paused'
            
        
        self._current_action.SetLabelText( current_action )
        
        if queue_paused:
            
            ClientGUICommon.SetBitmapButtonBitmap( self._pause_queue_button, CC.GlobalBMPs.play )
            
        else:
            
            ClientGUICommon.SetBitmapButtonBitmap( self._pause_queue_button, CC.GlobalBMPs.pause )
            
        
        if files_paused:
            
            ClientGUICommon.SetBitmapButtonBitmap( self._pause_files_button, CC.GlobalBMPs.play )
            
        else:
            
            ClientGUICommon.SetBitmapButtonBitmap( self._pause_files_button, CC.GlobalBMPs.pause )
            
        
    
    def CheckAbleToClose( self ):
        
        if self._simple_downloader_import.CurrentlyWorking():
            
            raise HydrusExceptions.VetoException( 'This page is still importing.' )
            
        
    
    def EventAdvance( self, event ):
        
        selection = self._pending_jobs_listbox.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            job = self._pending_jobs_listbox.GetClientData( selection )
            
            self._simple_downloader_import.AdvanceJob( job )
            
            self._UpdateStatus()
            
        
    
    def EventDelay( self, event ):
        
        selection = self._pending_jobs_listbox.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            job = self._pending_jobs_listbox.GetClientData( selection )
            
            self._simple_downloader_import.DelayJob( job )
            
            self._UpdateStatus()
            
        
    
    def EventDelete( self, event ):
        
        selection = self._pending_jobs_listbox.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            job = self._pending_jobs_listbox.GetClientData( selection )
            
            self._simple_downloader_import.DeleteJob( job )
            
            self._UpdateStatus()
            
        
    
    def EventFormulaChanged( self, event ):
        
        formula = self._formulae.GetChoice()
        
        formula_name = formula.GetName()
        
        self._simple_downloader_import.SetFormulaName( formula_name )
        self._controller.new_options.SetString( 'favourite_simple_downloader_formula', formula_name )
        
        event.Skip()
        
    
    def EventPauseQueue( self, event ):
        
        self._simple_downloader_import.PausePlayQueue()
        
        self._UpdateStatus()
        
    
    def EventPauseFiles( self, event ):
        
        self._simple_downloader_import.PausePlayFiles()
        
        self._UpdateStatus()
        
    
    def SetSearchFocus( self ):
        
        wx.CallAfter( self._page_url_input.SetFocus )
        
    
    def Start( self ):
        
        self._simple_downloader_import.Start( self._page_key )
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_IMPORT_SIMPLE_DOWNLOADER ] = ManagementPanelImporterSimpleDownloader

class ManagementPanelImporterWatcher( ManagementPanelImporter ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanelImporter.__init__( self, parent, page, controller, management_controller )
        
        self._watcher_panel = ClientGUICommon.StaticBox( self, 'watcher' )
        
        self._watcher_subject = ClientGUICommon.BetterStaticText( self._watcher_panel )
        
        self._url_input = wx.TextCtrl( self._watcher_panel, style = wx.TE_PROCESS_ENTER )
        self._url_input.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
        self._options_panel = wx.Panel( self._watcher_panel )
        
        #
        
        imports_panel = ClientGUICommon.StaticBox( self._options_panel, 'file imports' )
        
        self._files_pause_button = wx.BitmapButton( imports_panel, bitmap = CC.GlobalBMPs.pause )
        self._files_pause_button.Bind( wx.EVT_BUTTON, self.EventPauseFiles )
        
        self._current_action = ClientGUICommon.BetterStaticText( imports_panel )
        self._seed_cache_control = ClientGUISeedCache.SeedCacheStatusControl( imports_panel, self._controller, self._page_key )
        self._file_download_control = ClientGUIControls.NetworkJobControl( imports_panel )
        
        #
        
        checker_panel = ClientGUICommon.StaticBox( self._options_panel, 'checker' )
        
        self._file_velocity_status = ClientGUICommon.BetterStaticText( checker_panel )
        
        self._checking_pause_button = wx.BitmapButton( checker_panel, bitmap = CC.GlobalBMPs.pause )
        self._checking_pause_button.Bind( wx.EVT_BUTTON, self.EventPauseChecker )
        
        self._watcher_status = ClientGUICommon.BetterStaticText( checker_panel )
        
        self._check_now_button = wx.Button( checker_panel, label = 'check now' )
        self._check_now_button.Bind( wx.EVT_BUTTON, self.EventCheckNow )
        
        self._checker_options_button = ClientGUICommon.BetterButton( checker_panel, 'edit check timings', self._EditCheckerOptions )
        
        self._checker_download_control = ClientGUIControls.NetworkJobControl( checker_panel )
        
        #
        
        self._watcher_import = self._management_controller.GetVariable( 'watcher_import' )
        
        ( url, file_import_options, tag_import_options ) = self._watcher_import.GetOptions()
        
        ( namespaces, search_value ) = ClientDefaults.GetDefaultNamespacesAndSearchValue( ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_WATCHER ) )
        
        self._file_import_options = ClientGUIImport.FileImportOptionsButton( self._watcher_panel, file_import_options, self._watcher_import.SetFileImportOptions )
        self._tag_import_options = ClientGUIImport.TagImportOptionsButton( self._watcher_panel, namespaces, tag_import_options, self._watcher_import.SetTagImportOptions )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._current_action, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        hbox.Add( self._files_pause_button, CC.FLAGS_VCENTER )
        
        imports_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        imports_panel.Add( self._seed_cache_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        imports_panel.Add( self._file_download_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        gridbox = wx.FlexGridSizer( 2 )
        
        gridbox.AddGrowableCol( 0, 1 )
        
        gridbox.Add( self._file_velocity_status, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        gridbox.Add( self._checking_pause_button, CC.FLAGS_LONE_BUTTON )
        gridbox.Add( self._watcher_status, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        gridbox.Add( self._check_now_button, CC.FLAGS_VCENTER )
        
        checker_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        checker_panel.Add( self._checker_options_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        checker_panel.Add( self._checker_download_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( imports_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( checker_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._options_panel.SetSizer( vbox )
        
        self._watcher_panel.Add( self._watcher_subject, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._watcher_panel.Add( self._url_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._watcher_panel.Add( self._options_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        self._watcher_panel.Add( self._file_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._watcher_panel.Add( self._tag_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._sort_by, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._collect_by.Hide()
        
        vbox.Add( self._watcher_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        #
        
        seed_cache = self._watcher_import.GetSeedCache()
        
        self._seed_cache_control.SetSeedCache( seed_cache )
        
        self._watcher_import.SetDownloadControlFile( self._file_download_control )
        self._watcher_import.SetDownloadControlChecker( self._checker_download_control )
        
        self._url_input.SetValue( url )
        
        self._UpdateStatus()
        
    
    def _EditCheckerOptions( self ):
        
        checker_options = self._watcher_import.GetCheckerOptions()
        
        with ClientGUITopLevelWindows.DialogEdit( self._checker_options_button, 'edit check timings' ) as dlg:
            
            panel = ClientGUITime.EditCheckerOptions( dlg, checker_options )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                new_checker_options = panel.GetValue()
                
                self._watcher_import.SetCheckerOptions( new_checker_options )
                
                self._UpdateStatus()
                
            
        
    
    def _UpdateStatus( self ):
        
        if self._watcher_import.HasURL():
            
            self._url_input.SetEditable( False )
            
            if not self._options_panel.IsShown():
                
                self._watcher_subject.Show()
                
                self._options_panel.Show()
                
                self.Layout()
                
            
        else:
            
            if self._options_panel.IsShown():
                
                self._watcher_subject.Hide()
                
                self._options_panel.Hide()
                
                self.Layout()
                
            
        
        ( current_action, files_paused, file_velocity_status, next_check_time, watcher_status, subject, checking_status, check_now, checking_paused ) = self._watcher_import.GetStatus()
        
        if files_paused:
            
            if current_action == '':
                
                current_action = 'paused'
                
            else:
                
                current_action = 'pausing, ' + current_action
                
            
            ClientGUICommon.SetBitmapButtonBitmap( self._files_pause_button, CC.GlobalBMPs.play )
            
        else:
            
            ClientGUICommon.SetBitmapButtonBitmap( self._files_pause_button, CC.GlobalBMPs.pause )
            
        
        self._current_action.SetLabelText( current_action )
        
        self._file_velocity_status.SetLabelText( file_velocity_status )
        
        if checking_paused:
            
            if watcher_status == '':
                
                watcher_status = 'paused'
                
            
            ClientGUICommon.SetBitmapButtonBitmap( self._checking_pause_button, CC.GlobalBMPs.play )
            
        else:
            
            if watcher_status == '':
                
                watcher_status = 'next check ' + HydrusData.ConvertTimestampToPrettyPending( next_check_time )
                
            
            ClientGUICommon.SetBitmapButtonBitmap( self._checking_pause_button, CC.GlobalBMPs.pause )
            
        
        self._watcher_status.SetLabelText( watcher_status )
        
        if checking_status == ClientImporting.CHECKER_STATUS_404:
            
            self._checking_pause_button.Disable()
            
        elif checking_status == ClientImporting.CHECKER_STATUS_DEAD:
            
            self._checking_pause_button.Disable()
            
        else:
            
            self._checking_pause_button.Enable()
            
        
        if subject in ( '', 'unknown subject' ):
            
            subject = 'no subject'
            
        
        self._watcher_subject.SetLabelText( subject )
        
        if check_now:
            
            self._check_now_button.Disable()
            
        else:
            
            self._check_now_button.Enable()
            
        
    
    def CheckAbleToClose( self ):
        
        if self._watcher_import.HasURL():
            
            if self._watcher_import.CurrentlyWorking():
                
                raise HydrusExceptions.VetoException( 'This page is still importing.' )
                
            
        
    
    def EventCheckNow( self, event ):
        
        self._watcher_import.CheckNow()
        
        self._UpdateStatus()
        
    
    def EventPauseFiles( self, event ):
        
        self._watcher_import.PausePlayFiles()
        
        self._UpdateStatus()
        
    
    def EventPauseChecker( self, event ):
        
        self._watcher_import.PausePlayChecker()
        
        self._UpdateStatus()
        
    
    def EventKeyDown( self, event ):
        
        ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
        
        if key in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
            
            url = self._url_input.GetValue()
            
            if url == '':
                
                return
                
            
            self._url_input.SetEditable( False )
            
            self._watcher_import.SetURL( url )
            
            publish_to_page = True
            
            self._watcher_import.Start( self._page_key, publish_to_page )
            
        else:
            
            event.Skip()
            
        
    
    def SetSearchFocus( self ):
        
        wx.CallAfter( self._url_input.SetFocus )
        
    
    def Start( self ):
        
        if self._watcher_import.HasURL():
            
            publish_to_page = True
            
            self._watcher_import.Start( self._page_key, publish_to_page )
            
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_IMPORT_WATCHER ] = ManagementPanelImporterWatcher

class ManagementPanelImporterURLs( ManagementPanelImporter ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanelImporter.__init__( self, parent, page, controller, management_controller )
        
        #
        
        self._url_panel = ClientGUICommon.StaticBox( self, 'url downloader' )
        
        self._pause_button = wx.BitmapButton( self._url_panel, bitmap = CC.GlobalBMPs.pause )
        self._pause_button.Bind( wx.EVT_BUTTON, self.EventPause )
        
        self._overall_status = ClientGUICommon.BetterStaticText( self._url_panel )
        self._current_action = ClientGUICommon.BetterStaticText( self._url_panel )
        self._file_download_control = ClientGUIControls.NetworkJobControl( self._url_panel )
        self._overall_gauge = ClientGUICommon.Gauge( self._url_panel )
        
        self._urls_import = self._management_controller.GetVariable( 'urls_import' )
        
        # replace all this with a seed cache panel sometime
        self._seed_cache_button = ClientGUISeedCache.SeedCacheButton( self._url_panel, self._controller, self._urls_import.GetSeedCache )
        
        self._url_input = ClientGUIControls.TextAndPasteCtrl( self._url_panel, self._PendURLs )
        
        file_import_options = self._urls_import.GetOptions()
        
        self._file_import_options = ClientGUIImport.FileImportOptionsButton( self._url_panel, file_import_options, self._urls_import.SetFileImportOptions )
        
        #
        
        self._url_panel.Add( self._pause_button, CC.FLAGS_LONE_BUTTON )
        self._url_panel.Add( self._overall_status, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._url_panel.Add( self._current_action, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._url_panel.Add( self._overall_gauge, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._url_panel.Add( self._seed_cache_button, CC.FLAGS_LONE_BUTTON )
        self._url_panel.Add( self._file_download_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._url_panel.Add( self._url_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._url_panel.Add( self._file_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._sort_by, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._collect_by.Hide()
        
        vbox.Add( self._url_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        #
        
        self._urls_import.SetDownloadControlFile( self._file_download_control )
        
        self._UpdateStatus()
        
        HG.client_controller.sub( self, 'PendURL', 'pend_url' )
        
    
    def _PendURLs( self, urls ):
        
        urls = [ url for url in urls if url.startswith( 'http' ) ]
        
        self._urls_import.PendURLs( urls )
        
        self._UpdateStatus()
        
    
    def _UpdateStatus( self ):
        
        ( ( overall_status, ( overall_value, overall_range ) ), paused ) = self._urls_import.GetStatus()
        
        if self._overall_status.GetLabelText() != overall_status:
            
            self._overall_status.SetLabelText( overall_status )
            
        
        self._overall_gauge.SetRange( overall_range )
        self._overall_gauge.SetValue( overall_value )
        
        if overall_value < overall_range:
            
            if paused:
                
                current_action = 'paused at ' + HydrusData.ConvertValueRangeToPrettyString( overall_value + 1, overall_range )
                
            else:
                
                current_action = 'processing ' + HydrusData.ConvertValueRangeToPrettyString( overall_value + 1, overall_range )
                
            
        else:
            
            current_action = ''
            
        
        if self._current_action.GetLabelText() != current_action:
            
            self._current_action.SetLabelText( current_action )
            
        
        if paused:
            
            ClientGUICommon.SetBitmapButtonBitmap( self._pause_button, CC.GlobalBMPs.play )
            
        else:
            
            ClientGUICommon.SetBitmapButtonBitmap( self._pause_button, CC.GlobalBMPs.pause )
            
        
    
    def CheckAbleToClose( self ):
        
        if self._urls_import.CurrentlyWorking():
            
            raise HydrusExceptions.VetoException( 'This page is still importing.' )
            
        
    
    def EventPause( self, event ):
        
        self._urls_import.PausePlay()
        
        self._UpdateStatus()
        
    
    def PendURL( self, page_key, url ):
        
        if page_key == self._page_key:
            
            self._PendURLs( ( url, ) )
            
        
    
    def SetSearchFocus( self ):
        
        wx.CallAfter( self._url_input.SetFocus )
        
    
    def Start( self ):
        
        self._urls_import.Start( self._page_key )
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_IMPORT_URLS ] = ManagementPanelImporterURLs

class ManagementPanelPetitions( ManagementPanel ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        self._petition_service_key = management_controller.GetKey( 'petition_service' )
        
        ManagementPanel.__init__( self, parent, page, controller, management_controller )
        
        self._service = self._controller.services_manager.GetService( self._petition_service_key )
        self._can_ban = self._service.HasPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_OVERRULE )
        
        service_type = self._service.GetServiceType()
        
        self._num_petition_info = None
        self._current_petition = None
        
        #
        
        self._petitions_info_panel = ClientGUICommon.StaticBox( self, 'petitions info' )
        
        self._refresh_num_petitions_button = ClientGUICommon.BetterButton( self._petitions_info_panel, 'refresh counts', self._FetchNumPetitions )
        
        self._petition_types_to_controls = {}
        
        content_type_hboxes = []
        
        petition_types = []
        
        if service_type == HC.FILE_REPOSITORY:
            
            petition_types.append( ( HC.CONTENT_TYPE_FILES, HC.CONTENT_STATUS_PETITIONED ) )
            
        elif service_type == HC.TAG_REPOSITORY:
            
            petition_types.append( ( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_STATUS_PETITIONED ) )
            petition_types.append( ( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_STATUS_PENDING ) )
            petition_types.append( ( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_STATUS_PETITIONED ) )
            petition_types.append( ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_STATUS_PENDING ) )
            petition_types.append( ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_STATUS_PETITIONED ) )
            
        
        for ( content_type, status ) in petition_types:
            
            func = HydrusData.Call( self._FetchPetition, content_type, status )
            
            st = ClientGUICommon.BetterStaticText( self._petitions_info_panel )
            button = ClientGUICommon.BetterButton( self._petitions_info_panel, 'fetch ' + HC.content_status_string_lookup[ status ] + ' ' + HC.content_type_string_lookup[ content_type ] + ' petition', func )
            
            button.Disable()
            
            self._petition_types_to_controls[ ( content_type, status ) ] = ( st, button )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.Add( st, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
            hbox.Add( button, CC.FLAGS_VCENTER )
            
            content_type_hboxes.append( hbox )
            
        
        #
        
        self._petition_panel = ClientGUICommon.StaticBox( self, 'petition' )
        
        self._action_text = ClientGUICommon.BetterStaticText( self._petition_panel, label = '' )
        
        self._reason_text = ClientGUICommon.SaneMultilineTextCtrl( self._petition_panel, style = wx.TE_READONLY )
        self._reason_text.SetMinSize( ( -1, 80 ) )
        
        check_all = ClientGUICommon.BetterButton( self._petition_panel, 'check all', self._CheckAll )
        flip_selected = ClientGUICommon.BetterButton( self._petition_panel, 'flip selected', self._FlipSelected )
        check_none = ClientGUICommon.BetterButton( self._petition_panel, 'check none', self._CheckNone )
        
        self._contents = wx.CheckListBox( self._petition_panel, style = wx.LB_EXTENDED )
        self._contents.Bind( wx.EVT_LISTBOX_DCLICK, self.EventContentDoubleClick )
        
        self._process = wx.Button( self._petition_panel, label = 'process' )
        self._process.Bind( wx.EVT_BUTTON, self.EventProcess )
        self._process.SetForegroundColour( ( 0, 128, 0 ) )
        self._process.Disable()
        
        self._modify_petitioner = wx.Button( self._petition_panel, label = 'modify petitioner' )
        self._modify_petitioner.Bind( wx.EVT_BUTTON, self.EventModifyPetitioner )
        self._modify_petitioner.Disable()
        if not self._can_ban: self._modify_petitioner.Hide()
        
        #
        
        self._petitions_info_panel.Add( self._refresh_num_petitions_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        for hbox in content_type_hboxes:
            
            self._petitions_info_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
        
        check_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        check_hbox.Add( check_all, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        check_hbox.Add( flip_selected, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        check_hbox.Add( check_none, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        
        self._petition_panel.Add( ClientGUICommon.BetterStaticText( self._petition_panel, label = 'Double-click a petition to see its files, if it has them.' ), CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.Add( self._action_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.Add( self._reason_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.Add( check_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._petition_panel.Add( self._contents, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._petition_panel.Add( self._process, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.Add( self._modify_petitioner, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._sort_by, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( self._collect_by, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox.Add( self._petitions_info_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._petition_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        self._controller.sub( self, 'RefreshQuery', 'refresh_query' )
        
    
    def _CheckAll( self ):
        
        for i in range( self._contents.GetCount() ):
            
            self._contents.Check( i )
            
        
    
    def _CheckNone( self ):
        
        for i in range( self._contents.GetCount() ):
            
            self._contents.Check( i, False )
            
        
    
    def _DrawCurrentPetition( self ):
        
        if self._current_petition is None:
            
            self._action_text.SetLabelText( '' )
            self._reason_text.SetValue( '' )
            self._reason_text.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_WINDOW ) )
            self._contents.Clear()
            self._process.Disable()
            
            if self._can_ban:
                
                self._modify_petitioner.Disable()
                
            
        else:
            
            ( action_text, action_colour ) = self._current_petition.GetActionTextAndColour()
            
            self._action_text.SetLabelText( action_text )
            self._action_text.SetForegroundColour( action_colour )
            
            reason = self._current_petition.GetReason()
            
            self._reason_text.SetValue( reason )
            
            self._reason_text.SetBackgroundColour( action_colour )
            
            contents = self._current_petition.GetContents()
            
            def key( c ):
                
                if c.GetContentType() in ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_TYPE_TAG_PARENTS ):
                    
                    ( part_two, part_one ) = c.GetContentData()
                    
                elif c.GetContentType() == HC.CONTENT_TYPE_MAPPINGS:
                    
                    ( tag, hashes ) = c.GetContentData()
                    
                    part_one = tag
                    part_two = None
                    
                else:
                    
                    part_one = None
                    part_two = None
                    
                
                return ( -c.GetVirtualWeight(), part_one, part_two )
                
            
            contents.sort( key = key )
            
            self._contents.Clear()
            
            for content in contents:
                
                content_string = self._contents.EscapeMnemonics( content.ToString() )
                
                self._contents.Append( content_string, content )
                
            
            self._contents.SetChecked( range( self._contents.GetCount() ) )
            
            self._process.Enable()
            
            if self._can_ban:
                
                self._modify_petitioner.Enable()
                
            
        
        self._ShowHashes( [] )
        
    
    def _DrawNumPetitions( self ):
        
        new_petition_fetched = False
        
        for ( content_type, status, count ) in self._num_petition_info:
            
            petition_type = ( content_type, status )
            
            if petition_type in self._petition_types_to_controls:
                
                ( st, button ) = self._petition_types_to_controls[ petition_type ]
                
                st.SetLabelText( HydrusData.ConvertIntToPrettyString( count ) + ' petitions' )
                
                if count > 0:
                    
                    button.Enable()
                    
                    if self._current_petition is None and not new_petition_fetched:
                        
                        self._FetchPetition( content_type, status )
                        
                        new_petition_fetched = True
                        
                    
                else:
                    
                    button.Disable()
                    
                
            
        
    
    def _FetchNumPetitions( self ):
        
        def do_it( service ):
            
            def wx_draw( n_p_i ):
                
                if not self:
                    
                    return
                    
                
                self._num_petition_info = n_p_i
                
                self._DrawNumPetitions()
                
            
            def wx_reset():
                
                if not self:
                    
                    return
                    
                
                self._refresh_num_petitions_button.SetLabelText( 'refresh counts' )
                
            
            try:
                
                response = service.Request( HC.GET, 'num_petitions' )
                
                num_petition_info = response[ 'num_petitions' ]
                
                wx.CallAfter( wx_draw, num_petition_info )
                
            finally:
                
                wx.CallAfter( wx_reset )
                
            
        
        self._refresh_num_petitions_button.SetLabelText( u'Fetching\u2026' )
        
        self._controller.CallToThread( do_it, self._service )
        
    
    def _FetchPetition( self, content_type, status ):
        
        ( st, button ) = self._petition_types_to_controls[ ( content_type, status ) ]
        
        def wx_setpet( petition ):
            
            if not self:
                
                return
                
            
            self._current_petition = petition
            
            self._DrawCurrentPetition()
            
        
        def wx_done():
            
            if not self:
                
                return
                
            
            button.Enable()
            button.SetLabelText( 'fetch ' + HC.content_status_string_lookup[ status ] + ' ' + HC.content_type_string_lookup[ content_type ] + ' petition' )
            
        
        def do_it( service ):
            
            try:
                
                response = service.Request( HC.GET, 'petition', { 'content_type' : content_type, 'status' : status } )
                
                wx.CallAfter( wx_setpet, response[ 'petition' ] )
                
            finally:
                
                wx.CallAfter( wx_done )
                
            
        
        if self._current_petition is not None:
            
            self._current_petition = None
            
            self._DrawCurrentPetition()
            
        
        button.Disable()
        button.SetLabelText( u'Fetching\u2026' )
        
        self._controller.CallToThread( do_it, self._service )
        
    
    def _FlipSelected( self ):
        
        for i in self._contents.GetSelections():
            
            flipped_state = not self._contents.IsChecked( i )
            
            self._contents.Check( i, flipped_state )
            
        
    
    def _ShowHashes( self, hashes ):
        
        file_service_key = self._management_controller.GetKey( 'file_service' )
        
        with wx.BusyCursor():
            
            media_results = self._controller.Read( 'media_results', hashes )
            
        
        panel = ClientGUIMedia.MediaPanelThumbnails( self._page, self._page_key, file_service_key, media_results )
        
        panel.Collect( self._page_key, self._collect_by.GetChoice() )
        
        panel.Sort( self._page_key, self._sort_by.GetSort() )
        
        self._page.SwapMediaPanel( panel )
        
    
    def EventContentDoubleClick( self, event ):
        
        selections = self._contents.GetSelections()
        
        if len( selections ) > 0:
            
            selection = selections[0]
            
            content = self._contents.GetClientData( selection )
            
            if content.HasHashes():
                
                self._ShowHashes( content.GetHashes() )
                
            
        
    
    def EventProcess( self, event ):
        
        def break_approved_contents_into_chunks( approved_contents ):
            
            chunks_of_approved_contents = []
            chunk_of_approved_contents = []
            weight = 0
            
            for content in approved_contents:
                
                chunk_of_approved_contents.append( content )
                
                weight += content.GetVirtualWeight()
                
                if weight > 50:
                    
                    chunks_of_approved_contents.append( chunk_of_approved_contents )
                    
                    chunk_of_approved_contents = []
                    
                    weight = 0
                    
                
            
            if len( chunk_of_approved_contents ) > 0:
                
                chunks_of_approved_contents.append( chunk_of_approved_contents )
                
            
            return chunks_of_approved_contents
            
        
        def do_it( controller, service, petition_service_key, approved_contents, denied_contents, petition ):
            
            try:
                
                num_done = 0
                num_to_do = len( approved_contents )
                
                if len( denied_contents ) > 0:
                    
                    num_to_do += 1
                    
                
                if num_to_do > 1:
                    
                    job_key = ClientThreading.JobKey( cancellable = True )
                    
                    job_key.SetVariable( 'popup_title', 'comitting petitions' )
                    
                    HG.client_controller.pub( 'message', job_key )
                    
                else:
                    
                    job_key = None
                    
                
                chunks_of_approved_contents = break_approved_contents_into_chunks( approved_contents )
                
                for chunk_of_approved_contents in chunks_of_approved_contents:
                    
                    if job_key is not None:
                        
                        ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                        
                        if should_quit:
                            
                            return
                            
                        
                        job_key.SetVariable( 'popup_gauge_1', ( num_done, num_to_do ) )
                        
                    
                    ( update, content_updates ) = petition.GetApproval( chunk_of_approved_contents )
                    
                    service.Request( HC.POST, 'update', { 'client_to_server_update' : update } )
                    
                    controller.WriteSynchronous( 'content_updates', { petition_service_key : content_updates } )
                    
                    num_done += len( chunk_of_approved_contents )
                    
                
                if len( denied_contents ) > 0:
                    
                    if job_key is not None:
                        
                        ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                        
                        if should_quit:
                            
                            return
                            
                        
                    
                    update = petition.GetDenial( denied_contents )
                    
                    service.Request( HC.POST, 'update', { 'client_to_server_update' : update } )
                    
                
            finally:
                
                if job_key is not None:
                    
                    job_key.Delete()
                    
                
                def wx_fetch():
                    
                    if not self:
                        
                        return
                        
                    
                    self._FetchNumPetitions()
                    
                
                wx.CallAfter( wx_fetch )
                
            
        
        approved_contents = []
        denied_contents = []
        
        for index in range( self._contents.GetCount() ):
            
            content = self._contents.GetClientData( index )
            
            if self._contents.IsChecked( index ):
                
                approved_contents.append( content )
                
            else:
                
                denied_contents.append( content )
                
            
        
        HG.client_controller.CallToThread( do_it, self._controller, self._service, self._petition_service_key, approved_contents, denied_contents, self._current_petition )
        
        self._current_petition = None
        
        self._DrawCurrentPetition()
        
    
    def EventModifyPetitioner( self, event ):
        
        wx.MessageBox( 'modify users does not work yet!' )
        
        with ClientGUIDialogs.DialogModifyAccounts( self, self._petition_service_key, ( self._current_petition.GetPetitionerAccount(), ) ) as dlg:
            
            dlg.ShowModal()
            
        
    
    def RefreshQuery( self, page_key ):
        
        if page_key == self._page_key: self._DrawCurrentPetition()
        
    
    def Start( self ):
        
        wx.CallAfter( self._FetchNumPetitions )
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_PETITIONS ] = ManagementPanelPetitions

class ManagementPanelQuery( ManagementPanel ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanel.__init__( self, parent, page, controller, management_controller )
        
        file_search_context = self._management_controller.GetVariable( 'file_search_context' )
        
        self._search_enabled = self._management_controller.GetVariable( 'search_enabled' )
        
        self._query_job_key = ClientThreading.JobKey( cancellable = True )
        
        self._query_job_key.Finish()
        
        initial_predicates = file_search_context.GetPredicates()
        
        if self._search_enabled:
            
            self._search_panel = ClientGUICommon.StaticBox( self, 'search' )
            
            self._current_predicates_box = ClientGUIListBoxes.ListBoxTagsActiveSearchPredicates( self._search_panel, self._page_key, initial_predicates )
            
            synchronised = self._management_controller.GetVariable( 'synchronised' )
            
            self._searchbox = ClientGUIACDropdown.AutoCompleteDropdownTagsRead( self._search_panel, self._page_key, file_search_context, media_callable = self._page.GetMedia, synchronised = synchronised )
            
            self._cancel_search_button = ClientGUICommon.BetterBitmapButton( self._search_panel, CC.GlobalBMPs.stop, self._CancelSearch )
            
            self._cancel_search_button.Hide()
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.Add( self._searchbox, CC.FLAGS_EXPAND_BOTH_WAYS )
            hbox.Add( self._cancel_search_button, CC.FLAGS_VCENTER )
            
            self._search_panel.Add( self._current_predicates_box, CC.FLAGS_EXPAND_BOTH_WAYS )
            self._search_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._sort_by, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( self._collect_by, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        if self._search_enabled:
            
            vbox.Add( self._search_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        self._controller.sub( self, 'AddMediaResultsFromQuery', 'add_media_results_from_query' )
        self._controller.sub( self, 'SearchImmediately', 'notify_search_immediately' )
        self._controller.sub( self, 'RefreshQuery', 'refresh_query' )
        self._controller.sub( self, 'ChangeFileServicePubsub', 'change_file_service' )
        
    
    def _CancelSearch( self ):
        
        self._query_job_key.Cancel()
        
        self._UpdateCancelButton()
        
    
    def _MakeCurrentSelectionTagsBox( self, sizer ):
        
        tags_box = ClientGUICommon.StaticBoxSorterForListBoxTags( self, 'selection tags' )
        
        if self._search_enabled:
            
            t = ClientGUIListBoxes.ListBoxTagsSelectionManagementPanel( tags_box, self._page_key, predicates_callable = self._current_predicates_box.GetPredicates )
            
            file_search_context = self._management_controller.GetVariable( 'file_search_context' )
            
            tag_service_key = file_search_context.GetTagServiceKey()
            
            t.ChangeTagService( tag_service_key )
            
        else:
            
            t = ClientGUIListBoxes.ListBoxTagsSelectionManagementPanel( tags_box, self._page_key )
            
        
        tags_box.SetTagsBox( t )
        
        sizer.Add( tags_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        
    
    def _RefreshQuery( self ):
        
        self._controller.ResetIdleTimer()
        
        self._query_job_key.Cancel()
        
        if self._management_controller.GetVariable( 'search_enabled' ):
            
            if self._management_controller.GetVariable( 'synchronised' ):
                
                file_search_context = self._searchbox.GetFileSearchContext()
                
                current_predicates = self._current_predicates_box.GetPredicates()
                
                file_search_context.SetPredicates( current_predicates )
                
                self._management_controller.SetVariable( 'file_search_context', file_search_context )
                
                file_service_key = file_search_context.GetFileServiceKey()
                
                if len( current_predicates ) > 0:
                    
                    self._query_job_key = ClientThreading.JobKey()
                    
                    self._controller.CallToThread( self.THREADDoQuery, self._controller, self._page_key, self._query_job_key, file_search_context )
                    
                    panel = ClientGUIMedia.MediaPanelLoading( self._page, self._page_key, file_service_key )
                    
                else:
                    
                    panel = ClientGUIMedia.MediaPanelThumbnails( self._page, self._page_key, file_service_key, [] )
                    
                
                self._page.SwapMediaPanel( panel )
                
            
        else:
            
            self._sort_by.BroadcastSort()
            
        
    
    def _UpdateCancelButton( self ):
        
        if self._search_enabled:
            
            do_layout = False
            
            if self._query_job_key.IsDone():
                
                if self._cancel_search_button.IsShown():
                    
                    self._cancel_search_button.Hide()
                    
                    do_layout = True
                    
                
            else:
                
                # don't show it immediately to save on flickeriness on short queries
                
                WAIT_PERIOD = 3.0
                
                can_show = HydrusData.TimeHasPassedFloat( self._query_job_key.GetCreationTime() + WAIT_PERIOD )
                
                if can_show and not self._cancel_search_button.IsShown():
                    
                    self._cancel_search_button.Show()
                    
                    do_layout = True
                    
                
            
            if do_layout:
                
                self.Layout()
                
                self._searchbox.ForceSizeCalcNow()
                
            
        
    
    def AddMediaResultsFromQuery( self, query_job_key, media_results ):
        
        if query_job_key == self._query_job_key:
            
            self._controller.pub( 'add_media_results', self._page_key, media_results, append = False )
            
        
    
    def ChangeFileServicePubsub( self, page_key, service_key ):
        
        if page_key == self._page_key:
            
            self._management_controller.SetKey( 'file_service', service_key )
            
        
    
    def CleanBeforeDestroy( self ):
        
        ManagementPanel.CleanBeforeDestroy( self )
        
        self._query_job_key.Cancel()
        
    
    def GetPredicates( self ):
        
        if self._search_enabled:
            
            return self._current_predicates_box.GetPredicates()
            
        else:
            
            return []
            
        
    
    def RefreshQuery( self, page_key ):
        
        if page_key == self._page_key:
            
            self._RefreshQuery()
            
        
    
    def SearchImmediately( self, page_key, value ):
        
        if page_key == self._page_key:
            
            self._management_controller.SetVariable( 'synchronised', value )
            
            self._RefreshQuery()
            
        
    
    def SetSearchFocus( self ):
        
        if self._search_enabled:
            
            wx.CallAfter( self._searchbox.SetFocus )
            
        
    
    def ShowFinishedQuery( self, query_job_key, media_results ):
        
        if query_job_key == self._query_job_key:
            
            file_service_key = self._management_controller.GetKey( 'file_service' )
            
            panel = ClientGUIMedia.MediaPanelThumbnails( self._page, self._page_key, file_service_key, media_results )
            
            panel.Collect( self._page_key, self._collect_by.GetChoice() )
            
            panel.Sort( self._page_key, self._sort_by.GetSort() )
            
            self._page.SwapMediaPanel( panel )
            
        
    
    def Start( self ):
        
        file_search_context = self._management_controller.GetVariable( 'file_search_context' )
        
        initial_predicates = file_search_context.GetPredicates()
        
        if len( initial_predicates ) > 0 and not file_search_context.IsComplete():
            
            wx.CallAfter( self._RefreshQuery )
            
        
    
    def THREADDoQuery( self, controller, page_key, query_job_key, search_context ):
        
        def wx_code():
            
            query_job_key.Finish()
            
            if not self:
                
                return
                
            
            self.ShowFinishedQuery( query_job_key, media_results )
            
        
        QUERY_CHUNK_SIZE = 256
        
        query_hash_ids = controller.Read( 'file_query_ids', search_context, query_job_key )
        
        if query_job_key.IsCancelled():
            
            return
            
        
        media_results = []
        
        for sub_query_hash_ids in HydrusData.SplitListIntoChunks( query_hash_ids, QUERY_CHUNK_SIZE ):
            
            if query_job_key.IsCancelled():
                
                return
                
            
            more_media_results = controller.Read( 'media_results_from_ids', sub_query_hash_ids )
            
            media_results.extend( more_media_results )
            
            controller.pub( 'set_num_query_results', page_key, len( media_results ), len( query_hash_ids ) )
            
            controller.WaitUntilViewFree()
            
        
        search_context.SetComplete()
        
        wx.CallAfter( wx_code )
        
    
    def REPEATINGPageUpdate( self ):
        
        self._UpdateCancelButton()
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_QUERY ] = ManagementPanelQuery
