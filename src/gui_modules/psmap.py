"""!
@package psmap

@brief GUI for ps.map

Classes:
 - PsMapData    (to be moved - menudata.py)
 - PsMapToolbar (to be moved - toolbars.py)
 - PsMapFrame
 - PsMapBufferedWindow

(C) 2011 by Anna Kratochvilova, and the GRASS Development Team
This program is free software under the GNU General Public License
(>=v2). Read the file COPYING that comes with GRASS for details.

@author Anna Kratochvilova <anna.kratochvilova fsv.cvut.cz> (bachelor's project)
@author Martin Landa <landa.martin gmail.com> (mentor)
"""

import os

import globalvar
import menu
from   menudata   import MenuData, etcwxdir
from   toolbars   import AbstractToolbar
from   icon       import Icons

import wx

class PsMapData(MenuData):
    def __init__(self, path = None):
        """!Menu for Hardcopy Map Output Utility (psmap.py)
        
        @path path to XML to be read (None for menudata_psmap.xml)
        """
        if not path:
            gisbase = os.getenv('GISBASE')
            global etcwxdir
	    path = os.path.join(etcwxdir, 'xml', 'menudata_psmap.xml')
        
        MenuData.__init__(self, path)

class PsMapToolbar(AbstractToolbar):
    def __init__(self, parent):
        """!Toolbar Hardcopy Map Output Utility (psmap.py)
        
        @param parent parent window
        """
        AbstractToolbar.__init__(self, parent)
        
        self.InitToolbar(self._toolbarData())
        
        self.Realize()
        
    def _toolbarData(self):
        """!Toolbar data
        """
        self.quit = wx.NewId()
        
        # tool, label, bitmap, kind, shortHelp, longHelp, handler
        return (
            (self.quit, 'quit', Icons['quit'].GetBitmap(),
             wx.ITEM_NORMAL, Icons['quit'].GetLabel(), Icons['quit'].GetDesc(),
             self.parent.OnCloseWindow),
            )
    
class PsMapFrame(wx.Frame):
    def __init__(self, parent = None, id = wx.ID_ANY,
                 title = _("GRASS GIS Hardcopy Map Output Utility"), **kwargs):
        """!Main window of ps.map GUI
        
        @param parent parent window
        @param id window id
        @param title window title
        
        @param kwargs wx.Frames' arguments
        """
        self.parent = parent
        
        wx.Frame.__init__(self, parent = parent, id = id, title = title, name = "PsMap", **kwargs)
        self.SetIcon(wx.Icon(os.path.join(globalvar.ETCICONDIR, 'grass.ico'), wx.BITMAP_TYPE_ICO))
        
        self.menubar = menu.Menu(parent = self, data = PsMapData())
        self.SetMenuBar(self.menubar)
        
        self.toolbar = PsMapToolbar(parent = self)
        self.SetToolBar(self.toolbar)
        
        self.statusbar = self.CreateStatusBar(number = 1)
        
        self.canvas = PsMapBufferedWindow(parent = self)
        
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        
        self._layout()
        self.SetMinSize(wx.Size(640, 480))
        
    def _layout(self):
        """!Do layout
        """
        pass
    
    def OnCloseWindow(self, event):
        """!Close window"""
        self.Destroy()

class PsMapBufferedWindow(wx.Window):
    """!A buffered window class.
    
    @param parent parent window
    @param kwargs other wx.Window parameters
    """
    def __init__(self, parent, id =  wx.ID_ANY,
                 style = wx.NO_FULL_REPAINT_ON_RESIZE,
                 **kwargs):
        self.parent = parent
        # store an off screen empty bitmap for saving to file
        self._buffer = None
        # indicates whether or not a resize event has taken place
        self.resize = False 
        
        wx.Window.__init__(self, parent, id = id, style = style, **kwargs)
        
        self.pdc = wx.PseudoDC()
        
        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda x: None)
        
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE,  self.OnSize)
        self.Bind(wx.EVT_IDLE,  self.OnIdle)
        
    def Clear(self):
        """!Clear canvas
        """
        bg = wx.WHITE_BRUSH
        self.pdc.BeginDrawing()
        self.pdc.SetBackground(bg)
        self.pdc.Clear()
        self.Refresh()
        self.pdc.EndDrawing()
        
    def OnPaint(self, event):
        """!Draw pseudo DC to buffer
        """
        if not self._buffer:
            return
        
        dc = wx.BufferedPaintDC(self, self._buffer)
        
        # use PrepareDC to set position correctly
        self.PrepareDC(dc)
        
        dc.SetBackground(wx.WHITE_BRUSH)
        dc.Clear()
        
        # draw to the DC using the calculated clipping rect
        rgn = self.GetUpdateRegion()
        self.pdc.DrawToDCClipped(dc, rgn.GetBox())
        
    def OnSize(self, event):
        """!Init image size to match window size
        """
        event.Skip()
        
    def OnIdle(self, event):
        """!Only re-render a image during idle time instead of
        multiple times during resizing.
        """
        width, height = self.GetClientSize()
        # Make new off screen bitmap: this bitmap will always have the
        # current drawing in it, so it can be used to save the image
        # to a file, or whatever.
        self._buffer = wx.EmptyBitmap(width, height)
        
        # re-render image on idle
        self.resize = True
        
def main():
    app = wx.PySimpleApp()
    wx.InitAllImageHandlers()
    frame = PsMapFrame()
    frame.Show()
    
    app.MainLoop()

if __name__ == "__main__":
    main()
