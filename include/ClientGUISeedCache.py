import ClientConstants as CC
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIListCtrl
import ClientGUIMenus
import ClientGUISerialisable
import ClientGUIScrolledPanels
import ClientGUITopLevelWindows
import ClientImportSeeds
import ClientPaths
import ClientSerialisable
import ClientThreading
import HydrusConstants as HC
import HydrusData
import HydrusGlobals as HG
import HydrusPaths
import HydrusText
import os
import wx

class EditSeedCachePanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, controller, seed_cache ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._controller = controller
        self._seed_cache = seed_cache
        
        self._text = ClientGUICommon.BetterStaticText( self, 'initialising' )
        
        # add index control row here, hide it if needed and hook into showing/hiding and postsizechangedevent on seed add/remove
        
        columns = [ ( '#', 3 ), ( 'source', -1 ), ( 'status', 12 ), ( 'added', 23 ), ( 'last modified', 23 ), ( 'source time', 23 ), ( 'note', 20 ) ]
        
        self._list_ctrl = ClientGUIListCtrl.BetterListCtrl( self, 'seed_cache', 30, 30, columns, self._ConvertSeedToListCtrlTuples, delete_key_callback = self._DeleteSelected )
        
        #
        
        self._AddSeeds( self._seed_cache.GetSeeds() )
        
        self._list_ctrl.Sort( 0 )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._text, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._list_ctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self._list_ctrl.Bind( wx.EVT_RIGHT_DOWN, self.EventShowMenu )
        
        self._controller.sub( self, 'NotifySeedsUpdated', 'seed_cache_seeds_updated' )
        
        wx.CallAfter( self._UpdateText )
        
    
    def _AddSeeds( self, seeds ):
        
        self._list_ctrl.AddDatas( seeds )
        
    
    def _ConvertSeedToListCtrlTuples( self, seed ):
        
        seed_index = self._seed_cache.GetSeedIndex( seed )
        
        seed_data = seed.seed_data
        status = seed.status
        added = seed.created
        modified = seed.modified
        source_time = seed.source_time
        note = seed.note
        
        pretty_seed_index = HydrusData.ConvertIntToPrettyString( seed_index )
        pretty_seed_data = HydrusData.ToUnicode( seed_data )
        pretty_status = CC.status_string_lookup[ status ]
        pretty_added = HydrusData.ConvertTimestampToPrettyAgo( added ) + ' ago'
        pretty_modified = HydrusData.ConvertTimestampToPrettyAgo( modified ) + ' ago'
        
        if source_time is None:
            
            pretty_source_time = 'unknown'
            
        else:
            
            pretty_source_time = HydrusData.ConvertTimestampToHumanPrettyTime( source_time )
            
        
        pretty_note = note.split( os.linesep )[0]
        
        display_tuple = ( pretty_seed_index, pretty_seed_data, pretty_status, pretty_added, pretty_modified, pretty_source_time, pretty_note )
        sort_tuple = ( seed_index, seed_data, status, added, modified, source_time, note )
        
        return ( display_tuple, sort_tuple )
        
    
    def _CopySelectedNotes( self ):
        
        notes = []
        
        for seed in self._list_ctrl.GetData( only_selected = True ):
            
            note = seed.note
            
            if note != '':
                
                notes.append( note )
                
            
        
        if len( notes ) > 0:
            
            separator = os.linesep * 2
            
            text = separator.join( notes )
            
            HG.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def _CopySelectedSeedData( self ):
        
        seeds = self._list_ctrl.GetData( only_selected = True )
        
        if len( seeds ) > 0:
            
            separator = os.linesep * 2
            
            text = separator.join( ( seed.seed_data for seed in seeds ) )
            
            HG.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def _DeleteSelected( self ):
        
        seeds_to_delete = self._list_ctrl.GetData( only_selected = True )
        
        if len( seeds_to_delete ) > 0:
            
            message = 'Are you sure you want to delete all the selected entries?'
            
            with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    self._seed_cache.RemoveSeeds( seeds_to_delete )
                    
                
            
        
    
    def _OpenSelectedSeedData( self ):
        
        seeds = self._list_ctrl.GetData( only_selected = True )
        
        if len( seeds ) > 0:
            
            if len( seeds ) > 10:
                
                message = 'You have many objects selected--are you sure you want to open them all?'
                
                with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                    
                    if dlg.ShowModal() != wx.ID_YES:
                        
                        return
                        
                    
                
            
            if seeds[0].seed_data.startswith( 'http' ):
                
                for seed in seeds:
                    
                    ClientPaths.LaunchURLInWebBrowser( seed.seed_data )
                    
                
            else:
                
                try:
                    
                    for seed in seeds:
                        
                        HydrusPaths.OpenFileLocation( seed.seed_data )
                        
                    
                except Exception as e:
                    
                    wx.MessageBox( HydrusData.ToUnicode( e ) )
                    
                
            
        
    
    def _SetSelected( self, status_to_set ):
        
        seeds = self._list_ctrl.GetData( only_selected = True )
        
        for seed in seeds:
            
            seed.SetStatus( status_to_set )
            
        
        self._seed_cache.NotifySeedsUpdated( seeds )
        
    
    def _ShowMenuIfNeeded( self ):
        
        selected_seeds = self._list_ctrl.GetData( only_selected = True )
        
        if len( selected_seeds ) > 0:
            
            menu = wx.Menu()
            
            can_show_files_in_new_page = True in ( seed.HasHash() for seed in selected_seeds )
            
            if can_show_files_in_new_page:
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'open selected import files in a new page', 'Show all the known selected files in a new thumbnail page. This is complicated, so cannot always be guaranteed, even if the import says \'success\'.', self._ShowSelectionInNewPage )
                
                ClientGUIMenus.AppendSeparator( menu )
                
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'copy sources', 'Copy all the selected sources to clipboard.', self._CopySelectedSeedData )
            ClientGUIMenus.AppendMenuItem( self, menu, 'copy notes', 'Copy all the selected notes to clipboard.', self._CopySelectedNotes )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'open sources', 'Open all the selected sources in your file explorer or web browser.', self._OpenSelectedSeedData )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'try again', 'Reset the progress of all the selected imports.', HydrusData.Call( self._SetSelected, CC.STATUS_UNKNOWN ) )
            ClientGUIMenus.AppendMenuItem( self, menu, 'skip', 'Skip all the selected imports.', HydrusData.Call( self._SetSelected, CC.STATUS_SKIPPED ) )
            ClientGUIMenus.AppendMenuItem( self, menu, 'delete from list', 'Remove all the selected imports.', self._DeleteSelected )
            
            HG.client_controller.PopupMenu( self, menu )
            
        
    
    def _ShowSelectionInNewPage( self ):
        
        hashes = []
        
        for seed in self._list_ctrl.GetData( only_selected = True ):
            
            if seed.HasHash():
                
                hashes.append( seed.GetHash() )
                
            
        
        if len( hashes ) > 0:
            
            HG.client_controller.pub( 'new_page_query', CC.LOCAL_FILE_SERVICE_KEY, initial_hashes = hashes )
            
        
    
    def _UpdateListCtrl( self, seeds ):
        
        seeds_to_add = []
        seeds_to_update = []
        seeds_to_delete = []
        
        for seed in seeds:
            
            if self._seed_cache.HasSeed( seed ):
                
                if self._list_ctrl.HasData( seed ):
                    
                    seeds_to_update.append( seed )
                    
                else:
                    
                    seeds_to_add.append( seed )
                    
                
            else:
                
                if self._list_ctrl.HasData( seed ):
                    
                    seeds_to_delete.append( seed )
                    
                
            
        
        self._list_ctrl.DeleteDatas( seeds_to_delete )
        
        self._list_ctrl.UpdateDatas( seeds_to_update )
        
        self._AddSeeds( seeds_to_add )
        
    
    def _UpdateText( self ):
        
        ( status, ( total_processed, total ) ) = self._seed_cache.GetStatus()
        
        self._text.SetLabelText( status )
        
        self.Layout()
        
    
    def EventShowMenu( self, event ):
        
        wx.CallAfter( self._ShowMenuIfNeeded )
        
        event.Skip() # let the right click event go through before doing menu, in case selection should happen
        
    
    def GetValue( self ):
        
        return self._seed_cache
        
    
    def NotifySeedsUpdated( self, seed_cache_key, seeds ):
        
        if seed_cache_key == self._seed_cache.GetSeedCacheKey():
            
            self._UpdateText()
            self._UpdateListCtrl( seeds )
            
        
    
class SeedCacheButton( ClientGUICommon.BetterBitmapButton ):
    
    def __init__( self, parent, controller, seed_cache_get_callable, seed_cache_set_callable = None ):
        
        ClientGUICommon.BetterBitmapButton.__init__( self, parent, CC.GlobalBMPs.seed_cache, self._ShowSeedCacheFrame )
        
        self._controller = controller
        self._seed_cache_get_callable = seed_cache_get_callable
        self._seed_cache_set_callable = seed_cache_set_callable
        
        self.SetToolTip( 'open detailed file import status--right-click for quick actions, if applicable' )
        
        self.Bind( wx.EVT_RIGHT_DOWN, self.EventShowMenu )
        
    
    def _ClearSeeds( self, statuses_to_remove ):
        
        message = 'Are you sure you want to delete all the ' + '/'.join( ( CC.status_string_lookup[ status ] for status in statuses_to_remove ) ) + ' file import items? This is useful for cleaning up and de-laggifying a very large list, but be careful you aren\'t removing something you would want to revisit or what watcher/subscription may be using for future check time calculations.'
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                seed_cache = self._seed_cache_get_callable()
                
                seed_cache.RemoveSeedsByStatus( statuses_to_remove )
                
            
        
    
    def _GetExportableSourcesString( self ):
        
        seed_cache = self._seed_cache_get_callable()
        
        seeds = seed_cache.GetSeeds()
        
        sources = [ seed.seed_data for seed in seeds ]
        
        return os.linesep.join( sources )
        
    
    def _GetSourcesFromSourcesString( self, sources_string ):
        
        sources_string = HydrusData.ToUnicode( sources_string )
        
        sources = HydrusText.DeserialiseNewlinedTexts( sources_string )
        
        return sources
        
    
    def _ImportFromClipboard( self ):
        
        raw_text = HG.client_controller.GetClipboardText()
        
        sources = self._GetSourcesFromSourcesString( raw_text )
        
        try:
            
            self._ImportSources( sources )
            
        except:
            
            wx.MessageBox( 'Could not import!' )
            
            raise
            
        
    
    def _ImportFromPng( self ):
        
        with wx.FileDialog( self, 'select the png with the sources', wildcard = 'PNG (*.png)|*.png' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                path = HydrusData.ToUnicode( dlg.GetPath() )
                
                payload = ClientSerialisable.LoadFromPng( path )
                
                try:
                    
                    sources = self._GetSourcesFromSourcesString( payload )
                    
                    self._ImportSources( sources )
                    
                except:
                    
                    wx.MessageBox( 'Could not import!' )
                    
                    raise
                    
                
            
        
    
    def _ImportSources( self, sources ):
        
        seed_cache = self._seed_cache_get_callable()
        
        if sources[0].startswith( 'http' ):
            
            seed_type = ClientImportSeeds.SEED_TYPE_URL
            
        else:
            
            seed_type = ClientImportSeeds.SEED_TYPE_HDD
            
        
        seeds = [ ClientImportSeeds.Seed( seed_type, source ) for source in sources ]
        
        seed_cache.AddSeeds( seeds )
        
    
    def _ExportToPng( self ):
        
        payload = self._GetExportableSourcesString()
        
        with ClientGUITopLevelWindows.DialogNullipotent( self, 'export to png' ) as dlg:
            
            panel = ClientGUISerialisable.PngExportPanel( dlg, payload )
            
            dlg.SetPanel( panel )
            
            dlg.ShowModal()
            
        
    
    def _ExportToClipboard( self ):
        
        payload = self._GetExportableSourcesString()
        
        HG.client_controller.pub( 'clipboard', 'text', payload )
        
    
    def _RetryErrors( self ):
        
        message = 'Are you sure you want to retry all the files that encountered errors?'
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                seed_cache = self._seed_cache_get_callable()
                
                seed_cache.RetryFailures()
                
            
        
    
    def _ShowSeedCacheFrame( self ):
        
        seed_cache = self._seed_cache_get_callable()
        
        tlp = ClientGUICommon.GetTLP( self )
        
        if isinstance( tlp, wx.Dialog ):
            
            if self._seed_cache_set_callable is None: # throw up a dialog that edits the seed cache in place
                
                with ClientGUITopLevelWindows.DialogNullipotent( self, 'file import status' ) as dlg:
                    
                    panel = EditSeedCachePanel( dlg, self._controller, seed_cache )
                    
                    dlg.SetPanel( panel )
                    
                    dlg.ShowModal()
                    
                
            else: # throw up a dialog that edits the seed cache but can be cancelled
                
                dupe_seed_cache = seed_cache.Duplicate()
                
                with ClientGUITopLevelWindows.DialogEdit( self, 'file import status' ) as dlg:
                    
                    panel = EditSeedCachePanel( dlg, self._controller, dupe_seed_cache )
                    
                    dlg.SetPanel( panel )
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        self._seed_cache_set_callable( dupe_seed_cache )
                        
                    
                
            
        else: # throw up a frame that edits the seed cache in place
            
            title = 'file import status'
            frame_key = 'file_import_status'
            
            frame = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( self, title, frame_key )
            
            panel = EditSeedCachePanel( frame, self._controller, seed_cache )
            
            frame.SetPanel( panel )
            
        
    
    def EventShowMenu( self, event ):
        
        menu = wx.Menu()
        
        seed_cache = self._seed_cache_get_callable()
        
        num_seeds = len( seed_cache )
        num_successful = seed_cache.GetSeedCount( CC.STATUS_SUCCESSFUL_AND_NEW ) + seed_cache.GetSeedCount( CC.STATUS_SUCCESSFUL_BUT_REDUNDANT )
        num_deleted_and_vetoed = seed_cache.GetSeedCount( CC.STATUS_DELETED ) + seed_cache.GetSeedCount( CC.STATUS_VETOED )
        num_errors = seed_cache.GetSeedCount( CC.STATUS_ERROR )
        num_skipped = seed_cache.GetSeedCount( CC.STATUS_SKIPPED )
        
        if num_errors > 0:
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'retry ' + HydrusData.ConvertIntToPrettyString( num_errors ) + ' error failures', 'Tell this cache to reattempt all its error failures.', self._RetryErrors )
            
        
        if num_successful > 0:
            
            num_deletees = num_successful
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'delete ' + HydrusData.ConvertIntToPrettyString( num_deletees ) + ' successful file import items from the queue', 'Tell this cache to clear out successful files, reducing the size of the queue.', self._ClearSeeds, ( CC.STATUS_SUCCESSFUL_AND_NEW, CC.STATUS_SUCCESSFUL_BUT_REDUNDANT ) )
            
        
        if num_deleted_and_vetoed > 0:
            
            num_deletees = num_deleted_and_vetoed
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'delete ' + HydrusData.ConvertIntToPrettyString( num_deletees ) + ' deleted/ignored file import items from the queue', 'Tell this cache to clear out processed files, reducing the size of the queue.', self._ClearSeeds, ( CC.STATUS_DELETED, CC.STATUS_VETOED ) )
            
        
        if num_errors + num_skipped > 0:
            
            num_deletees = num_errors + num_skipped
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'delete ' + HydrusData.ConvertIntToPrettyString( num_deletees ) + ' error/skipped file import items from the queue', 'Tell this cache to clear out all non-unknown files, reducing the size of the queue.', self._ClearSeeds, ( CC.STATUS_ERROR, CC.STATUS_SKIPPED ) )
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        if len( seed_cache ) > 0:
            
            submenu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, submenu, 'to clipboard', 'Copy all the sources in this list to the clipboard.', self._ExportToClipboard )
            ClientGUIMenus.AppendMenuItem( self, submenu, 'to png', 'Export all the sources in this list to a png file.', self._ExportToPng )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'export all sources' )
            
        
        submenu = wx.Menu()
        
        ClientGUIMenus.AppendMenuItem( self, submenu, 'from clipboard', 'Import new urls or paths to this list from the clipboard.', self._ImportFromClipboard )
        ClientGUIMenus.AppendMenuItem( self, submenu, 'from png', 'Import new urls or paths to this list from a png file.', self._ImportFromPng )
        
        ClientGUIMenus.AppendMenu( menu, submenu, 'import new sources' )
        
        HG.client_controller.PopupMenu( self, menu )
        
    
class SeedCacheStatusControl( wx.Panel ):
    
    def __init__( self, parent, controller, page_key = None ):
        
        wx.Panel.__init__( self, parent, style = wx.BORDER_DOUBLE )
        
        self._controller = controller
        self._page_key = page_key
        
        self._seed_cache = None
        
        self._import_summary_st = ClientGUICommon.BetterStaticText( self )
        self._progress_st = ClientGUICommon.BetterStaticText( self )
        
        self._seed_cache_button = SeedCacheButton( self, self._controller, self._GetSeedCache )
        
        self._progress_gauge = ClientGUICommon.Gauge( self )
        
        #
        
        self._Update()
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._progress_st, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        hbox.Add( self._seed_cache_button, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._import_summary_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( self._progress_gauge, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        #
        
        HG.client_controller.gui.RegisterUIUpdateWindow( self )
        
    
    def _GetSeedCache( self ):
        
        return self._seed_cache
        
    
    def _Update( self ):
        
        if self._seed_cache is None:
            
            self._import_summary_st.SetLabelText( '' )
            self._progress_st.SetLabelText( '' )
            self._progress_gauge.SetRange( 1 )
            self._progress_gauge.SetValue( 0 )
            
            if self._seed_cache_button.IsEnabled():
                
                self._seed_cache_button.Disable()
                
            
        else:
            
            ( import_summary, ( num_done, num_to_do ) ) = self._seed_cache.GetStatus()
            
            self._import_summary_st.SetLabelText( import_summary )
            
            if num_to_do == 0:
                
                self._progress_st.SetLabelText( '' )
                
            else:
                
                self._progress_st.SetLabelText( HydrusData.ConvertValueRangeToPrettyString( num_done, num_to_do ) )
                
            
            self._progress_gauge.SetRange( num_to_do )
            self._progress_gauge.SetValue( num_done )
            
            if not self._seed_cache_button.IsEnabled():
                
                self._seed_cache_button.Enable()
                
            
        
    
    def SetSeedCache( self, seed_cache ):
        
        if not self:
            
            return
            
        
        self._seed_cache = seed_cache
        
    
    def TIMERUIUpdate( self ):
        
        do_it_anyway = False
        
        if self._seed_cache is not None:
            
            ( import_summary, ( num_done, num_to_do ) ) = self._seed_cache.GetStatus()
            
            ( old_num_done, old_num_to_do ) = self._progress_gauge.GetValueRange()
            
            if old_num_done != num_done or old_num_to_do != num_to_do:
                
                if self._page_key is not None:
                    
                    do_it_anyway = True # to update the gauge
                    
                    HG.client_controller.pub( 'refresh_page_name', self._page_key )
                    
                
            
        
        if self._controller.gui.IShouldRegularlyUpdate( self ) or do_it_anyway:
            
            self._Update()
            
        
    
