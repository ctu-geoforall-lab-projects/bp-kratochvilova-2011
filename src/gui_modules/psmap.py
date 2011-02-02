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
import sys
import tempfile
from math import ceil
from collections import namedtuple

import grass.script as grass
if int(grass.version()['version'].split('.')[0]) > 6:
    sys.path.append(os.path.join(os.getenv('GISBASE'), 'etc', 'gui', 'wxpython',
                                 'gui_modules'))
else:
    sys.path.append(os.path.join(os.getenv('GISBASE'), 'etc', 'wxpython',
                                 'gui_modules'))
import globalvar
import menu
from   menudata   import MenuData, etcwxdir
from   gselect    import Select
from   toolbars   import AbstractToolbar
from   icon       import Icons
from   gcmd       import RunCommand
from grass.script import core as grass
from psmap_dialogs import *

import wx
import wx.lib.scrolledpanel as scrolled

try:
    from agw import flatnotebook as fnb
except ImportError: # if it's not there locally, try the wxPython lib.
    import wx.lib.agw.flatnotebook as fnb

        
    
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
        
        self.action = { 'id' : self.pointer }
        self.defaultAction = { 'id' : self.pointer,
                               'bind' : self.parent.OnPointer }
        self.OnTool(None)

        
    def _toolbarData(self):
        """!Toolbar data
        """
        self.quit = wx.NewId()
        self.pagesetup = wx.NewId()
        self.pointer = wx.NewId()
        self.zoomIn = wx.NewId()
        self.zoomOut = wx.NewId()
        self.zoomAll = wx.NewId()
        self.addMap = wx.NewId()
        self.dec = wx.NewId()
        self.delete = wx.NewId()
        self.instructionFile = wx.NewId()
        self.generatePS = wx.NewId()
        self.pan = wx.NewId()
        
        # tool, label, bitmap, kind, shortHelp, longHelp, handler
        return (
            (self.pagesetup, 'page setup', Icons['settings'].GetBitmap(),
             wx.ITEM_NORMAL, "Page setup", "Specify paper size, margins and orientation",
             self.parent.OnPageSetup),
            ("", "", "", "", "", "", ""),
            (self.pointer, "pointer", Icons["pointer"].GetBitmap(),
             wx.ITEM_CHECK, Icons["pointer"].GetLabel(), Icons["pointer"].GetDesc(),
             self.parent.OnPointer),
            (self.pan, 'pan', Icons['pan'].GetBitmap(),
             wx.ITEM_CHECK, Icons["pan"].GetLabel(), Icons["pan"].GetDesc(),
             self.parent.OnPan),
            (self.zoomIn, "zoomin", Icons["zoom_in"].GetBitmap(),
             wx.ITEM_CHECK, Icons["zoom_in"].GetLabel(), Icons["zoom_in"].GetDesc(),
             self.parent.OnZoomIn),
            (self.zoomOut, "zoomout", Icons["zoom_out"].GetBitmap(),
             wx.ITEM_CHECK, Icons["zoom_out"].GetLabel(), Icons["zoom_out"].GetDesc(),
             self.parent.OnZoomOut),
            (self.zoomAll, 'full extent', Icons['zoom_extent'].GetBitmap(),
             wx.ITEM_NORMAL, "Full extent", "Zoom to full extent",
             self.parent.OnZoomAll),
            ("", "", "", "", "", "", ""),
            (self.addMap, 'add map', Icons['addrast'].GetBitmap(),
             wx.ITEM_CHECK, "Raster map", "Click and drag to place raster map",
             self.parent.OnAddMap),
            (self.dec, "overlay", Icons["overlay"].GetBitmap(),
             wx.ITEM_NORMAL, Icons["overlay"].GetLabel(), Icons["overlay"].GetDesc(),
             self.parent.OnDecoration),
            (self.delete, "delete", Icons["delcmd"].GetBitmap(),
             wx.ITEM_NORMAL, "delete", "Delete selected object",
             self.parent.OnDelete),
            ("", "", "", "", "", "", ""),
            (self.instructionFile, 'generate', Icons['savefile'].GetBitmap(),
             wx.ITEM_NORMAL, "Generate file", "Generate mapping instruction file",
             self.parent.OnInstructionFile),
            (self.generatePS, 'generatePS', Icons['modelToImage'].GetBitmap(),
             wx.ITEM_NORMAL, "Create PS file", "Create PostScript file",
             self.parent.PSFile),
            ("", "", "", "", "", "", ""),
            (self.quit, 'quit', Icons['quit'].GetBitmap(),
             wx.ITEM_NORMAL, Icons['quit'].GetLabel(), Icons['quit'].GetDesc(),
             self.parent.OnCloseWindow)
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
        #menubar
        self.menubar = menu.Menu(parent = self, data = PsMapData())
        self.SetMenuBar(self.menubar)
        #toolbar

        self.toolbar = PsMapToolbar(parent = self)
        self.SetToolBar(self.toolbar)
        
        self.actionOld = self.toolbar.action['id']
        self.iconsize = (16, 16)
        #satusbar
        self.statusbar = self.CreateStatusBar(number = 1)
        
        self.dialogDict = {}  
        self.SetDefault()
        
        # mouse attributes -- position on the screen, begin and end of
        # dragging, and type of drawing
        self.mouse = {
            'begin': [0, 0], # screen coordinates
            'end'  : [0, 0],
            'use'  : "pointer",
            }
        # available cursors
        self.cursors = {
            "default" : wx.StockCursor(wx.CURSOR_ARROW),
            "cross"   : wx.StockCursor(wx.CURSOR_CROSS),
            "hand"    : wx.StockCursor(wx.CURSOR_HAND),
            #"pencil"  : wx.StockCursor(wx.CURSOR_PENCIL),
            #"sizenwse": wx.StockCursor(wx.CURSOR_SIZENWSE)
            }
        # pen and brush
        self.pen = {
            'paper': wx.Pen(colour = "BLACK", width = 1),
            'margins': wx.Pen(colour = "GREY", width = 1),
            'map': wx.Pen(colour = "GREEN", width = 1),
            'rasterLegend': wx.Pen(colour = "YELLOW", width = 1),
            'mapinfo': wx.Pen(colour = "YELLOW", width = 1),
            'box': wx.Pen(colour = 'RED', width = 2, style = wx.SHORT_DASH),
            'select': wx.Pen(colour = 'BLACK', width = 1, style = wx.SHORT_DASH)
            }
        self.brush = {
            'paper': wx.WHITE_BRUSH,
            'margins': wx.TRANSPARENT_BRUSH,            
            'map': wx.CYAN_BRUSH,
            'rasterLegend': wx.GREEN_BRUSH,
            'mapinfo': wx.RED_BRUSH,
            'box': wx.TRANSPARENT_BRUSH,
            'select':wx.TRANSPARENT_BRUSH
            }    
        self.canvas = PsMapBufferedWindow(parent = self, mouse = self.mouse, pen = self.pen,
                                            brush = self.brush, cursors = self.cursors, settings = self.dialogDict)
        self.canvas.SetCursor(self.cursors["default"])
        
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        
        self._layout()
        self.SetMinSize(wx.Size(700, 600))
        
        
    def DefaultData(self):
        """! Default settings"""
        self.defaultDict = {}
        #page
        self.defaultDict['page'] = dict(Units = 'inch', Format = 'a4', Orientation = 'Portrait',
                                        Width = 8.268, Height = 11.693, Left = 0.5, Right = 0.5, Top = 1, Bottom = 1)

        #map
        self.defaultDict['map'] = dict(raster = None, rect = None, scaleType = 0, scale = None) 
        #rasterLegend
        page = self.defaultDict['page']
        self.defaultDict['rasterLegend'] = dict(rLegend = False, unit = 'inch', rasterDefault = True, raster = None,
                                                discrete = None, type = None,
                                                where = (page['Left'], page['Top']), defaultSize = True,
                                                width = 0, height = 0, cols = 1, font = 'Helvetica', fontsize = 10, 
                                                color = 'black', tickbar = False, range = False, min = 0, max = 0,
                                                nodata = False)
        #mapinfo
        self.defaultDict['mapinfo'] = dict(isInfo = False, unit = 'inch', where = (page['Left'], page['Top']),
                                            font = 'Helvetica', fontsize = 10, color = 'black', background = 'none', 
                                            border = 'none')
        
    def SetDefault(self, type = None):
        """!Set default values"""
        self.DefaultData()
        if type is not None:
            self.dialogDict[type] = self.defaultDict[type]
        else:
            for key in self.defaultDict.keys():
                self.dialogDict[key] = self.defaultDict[key]
            
    def _layout(self):
        """!Do layout
        """
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        self.book = fnb.FlatNotebook(self, wx.ID_ANY, style = fnb.FNB_BOTTOM)
        self.book.AddPage(self.canvas, "Page 1")
        self.book.AddPage(wx.Panel(self), "Page 2")
        mainSizer.Add(self.book,1, wx.EXPAND)
        
        self.SetSizer(mainSizer)
        mainSizer.Fit(self)

            
    def InstructionFile(self):
        """!Creates list of mapping instructions"""
        instruction = []
        #change region
        if self.dialogDict['map']['scaleType'] == 1: #fixed scale
            region = grass.region()
            comment = "# set region: g.region n={n} s={s} e={e} w={w}".format(**region)
            instruction.append(comment)
        # paper
        if self.dialogDict['page']['Format'] == 'custom':
            paperInstruction = "paper\n    width {Width}\n    height {Height}\n".format(**self.dialogDict['page'])
        else:
            paperInstruction = "paper {Format}\n".format(**self.dialogDict['page'])
        paperInstruction += "    left {Left}\n    right {Right}\n"    \
                            "    bottom {Bottom}\n    top {Top}\nend".format(**self.dialogDict['page'])
                        
        instruction.append(paperInstruction)
        # raster
        rasterInstruction = ''
        if self.dialogDict['map']['raster']:
            rasterInstruction = "raster {raster}".format(**self.dialogDict['map'])
        instruction.append(rasterInstruction)
        #maploc
        if self.dialogDict['map']['rect'] is not None:
            maplocInstruction = "maploc {rect.x} {rect.y} {rect.width} {rect.height}".format(**self.dialogDict['map'])
            instruction.append(maplocInstruction)
        
        #scale
        if self.dialogDict['map']['scaleType'] == 1: #fixed scale
            scaleInstruction =  "# not necessary to set scale because of new region settings\n"\
                                "# scale 1:{0:.0f}".format(1/self.dialogDict['map']['scale'])
            instruction.append(scaleInstruction)
        #colortable
        if self.dialogDict['rasterLegend']['rLegend']:
            rLegendInstruction = "colortable y\n"
            rLegendInstruction += "    raster {raster}\n".format(**self.dialogDict['rasterLegend'])
            rLegendInstruction += "    where {where[0]} {where[1]}\n".format(**self.dialogDict['rasterLegend'])
            if not self.dialogDict['rasterLegend']['defaultSize']:
                rLegendInstruction += "    width {width}\n".format(**self.dialogDict['rasterLegend'])
            rLegendInstruction += "    discrete {discrete}\n".format(**self.dialogDict['rasterLegend'])
            if self.dialogDict['rasterLegend']['discrete'] == 'n':
                if not self.dialogDict['rasterLegend']['defaultSize']:
                    rLegendInstruction += "    height {height}\n".format(**self.dialogDict['rasterLegend'])
                rLegendInstruction += "    tickbar {tickbar}\n".format(**self.dialogDict['rasterLegend'])
                if self.dialogDict['rasterLegend']['range']:
                    rLegendInstruction += "    range {min} {max}\n".format(**self.dialogDict['rasterLegend'])
            else:
                rLegendInstruction += "    cols {cols}\n".format(**self.dialogDict['rasterLegend'])
                rLegendInstruction += "    nodata {nodata}\n".format(**self.dialogDict['rasterLegend'])
            rLegendInstruction += "    font {font}\n    fontsize {fontsize}\n    color {color}\n"\
                                    .format(**self.dialogDict['rasterLegend'])
            rLegendInstruction += "end"
            instruction.append(rLegendInstruction)
        
        return '\n'.join(instruction) + '\nend' 
    
    def PSFile(self, event):
        filename = self.getFile(wildcard = "PostScript (*.ps)|*.ps|Encapsulated PostScript (*.eps)|*.eps")
        if filename:
            instrFile = tempfile.NamedTemporaryFile(mode = 'w')
            instrFile.file.write(self.InstructionFile())
            instrFile.file.flush()
            flags = ''
            if os.path.splitext(filename)[1] == '.eps':
                flags = flags + 'e'
            if self.dialogDict['page']['Orientation'] == 'Landscape':
                flags = flags + 'r'
            RunCommand('ps.map', flags = flags, read = False, 
                        input = instrFile.name, output = filename)
                
                    
    def getFile(self, wildcard):
        suffix = []
        for filter in wildcard.split('|')[1::2]:
            s = filter.strip('*').split('.')[1]
            if s:
                s = '.' + s
            suffix.append(s)
            
        if self.dialogDict['map']['raster']:
            mapName = self.dialogDict['map']['raster'].split('@')[0] + suffix[0]
        else:
            mapName = ''
            
        filename = ''
        dlg = wx.FileDialog(self, message = "Save file as", defaultDir = "", 
                            defaultFile = mapName, wildcard = wildcard,
                            style = wx.CHANGE_DIR|wx.SAVE|wx.OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetPath()
            suffix = suffix[dlg.GetFilterIndex()]
            if not os.path.splitext(filename)[1]:
                filename = filename + suffix
            elif os.path.splitext(filename)[1] != suffix and suffix != '':
                filename = os.path.splitext(filename)[0] + suffix
            
        dlg.Destroy()
        return filename
                        
    def OnInstructionFile(self, event):
        filename = self.getFile(wildcard = "All files(*.*)|*.*|Text file|*.txt")        
        if filename:    
            instrFile = open(filename, "w")
            instrFile.write(self.InstructionFile())
            instrFile.close()            
        
    def OnPageSetup(self, event = None):
        """!Specify paper size, margins and orientation"""
        dlg = PageSetupDialog(self, settings = self.dialogDict) 
        dlg.CenterOnScreen()
        val = dlg.ShowModal()
        if val == wx.ID_OK:
            self.dialogDict['page'] = dlg.getInfo()
            self.canvas.SetPage()
        dlg.Destroy()
    def OnPointer(self, event):
        self.toolbar.OnTool(event)
        self.mouse["use"] = "pointer"
        self.canvas.SetCursor(self.cursors["default"])
        
    def OnPan(self, event):
        self.toolbar.OnTool(event)
        self.mouse["use"] = "pan"
        self.canvas.SetCursor(self.cursors["hand"])
            
    def OnZoomIn(self, event):
        self.toolbar.OnTool(event)
        self.mouse["use"] = "zoomin"
        self.canvas.SetCursor(self.cursors["cross"])
        
    def OnZoomOut(self, event):
        self.toolbar.OnTool(event)
        self.mouse["use"] = "zoomout"
        self.canvas.SetCursor(self.cursors["cross"])
        
    def OnZoomAll(self, event):
        self.mouseOld = self.mouse['use']
        self.cursorOld = self.canvas.GetCursor()
        self.mouse["use"] = "zoomin"
        self.canvas.ZoomAll() 
        self.mouse["use"] = self.mouseOld 
        self.canvas.SetCursor(self.cursorOld)  
        
    def OnAddMap(self, event):
        id = self.find_key(self.canvas.itemType, 'map')
        if event.GetId() != self.toolbar.action['id']:
            self.actionOld = self.toolbar.action['id']
            self.mouseOld = self.mouse['use']
            self.cursorOld = self.canvas.GetCursor()
        self.toolbar.OnTool(event)
        if id: # map exists
            assert len(id) == 1, 'Object map must be only one'
            id = id[0]
            dlg = MapDialog(parent = self, settings = self.dialogDict)
            val = dlg.ShowModal()
            if val == wx.ID_OK:
                self.dialogDict['map'] = dlg.getInfo()
                rectCanvas = self.canvas.CanvasPaperCoordinates(rect = self.dialogDict['map']['rect'],
                                                                    canvasToPaper = False)
    
                self.canvas.pdcTmp.RemoveAll()
                self.canvas.Draw( pen = self.pen[self.canvas.itemType[id]], brush = self.brush[self.canvas.itemType[id]],
                                pdc = self.canvas.pdcObj, drawid = id, pdctype = 'rect', bb = rectCanvas)
                # redraw select box if necessary                
                if self.canvas.dragId == id: 
                    self.canvas.Draw(pen = self.pen['select'], brush = self.brush['select'],
                                    pdc = self.canvas.pdcTmp, drawid = self.canvas.idBoxTmp,
                                    pdctype = 'rect', bb = rectCanvas.Inflate(3,3))
                    
                dlg.Destroy()
            
            self.canvas.SetCursor(self.cursorOld)  
            self.toolbar.ToggleTool(self.toolbar.action['id'], False)
            self.toolbar.action['id'] = self.actionOld
            self.toolbar.ToggleTool(self.actionOld, True)# bug, this should work
        else:    # sofar no map
            self.mouse["use"] = "addMap"
            self.canvas.SetCursor(self.cursors["cross"])
            
    def OnDecoration(self, event):
        """!Decorations overlay menu
        """
        decmenu = wx.Menu()
        # legend
        AddLegend = wx.MenuItem(decmenu, wx.ID_ANY, Icons["addlegend"].GetLabel())
        AddLegend.SetBitmap(Icons["addlegend"].GetBitmap(self.iconsize))
        decmenu.AppendItem(AddLegend)
        self.Bind(wx.EVT_MENU, self.OnAddLegend, AddLegend)
        # mapinfo
        AddMapinfo = wx.MenuItem(decmenu, wx.ID_ANY, "Add mapinfo")
        AddMapinfo.SetBitmap(Icons["addlegend"].GetBitmap(self.iconsize))
        decmenu.AppendItem(AddMapinfo)
        self.Bind(wx.EVT_MENU, self.OnAddMapinfo, AddMapinfo) 
        # Popup the menu.  If an item is selected then its handler
        # will be called before PopupMenu returns.
        self.PopupMenu(decmenu)
        decmenu.Destroy()
        
    def OnAddLegend(self, event):
        id = self.find_key(self.canvas.itemType, 'rasterLegend')
        id = id[0] if id else None
        dlg = LegendDialog(self, settings = self.dialogDict)
        if dlg.ShowModal() == wx.ID_OK:
            self.dialogDict['rasterLegend'] = dlg.getInfo()
            if self.dialogDict['rasterLegend']['rLegend']:
                if not id:
                    id = wx.NewId()
                    self.canvas.itemType[id] = 'rasterLegend'
                    self.canvas.objectId.append(id)
                drawRectangle = self.canvas.CanvasPaperCoordinates(rect = self.dialogDict['rasterLegend']['rect'], canvasToPaper = False)
                self.canvas.Draw( pen = self.pen[self.canvas.itemType[id]], brush = self.brush[self.canvas.itemType[id]],
                                pdc = self.canvas.pdcObj, drawid = id, pdctype = 'rect', bb = drawRectangle)
                self.canvas.pdcTmp.RemoveAll()
                self.canvas.dragId = -1
            else: 
                if id:
                    self.deleteObject(id)
                    self.canvas.pdcTmp.RemoveAll()
                    self.canvas.dragId = -1
        dlg.Destroy()

    def OnAddMapinfo(self, event):
        id = self.find_key(self.canvas.itemType, 'mapinfo')
        id = id[0] if id else None
        dlg = MapinfoDialog(self, settings = self.dialogDict)
        if dlg.ShowModal() == wx.ID_OK:
            self.dialogDict['mapinfo'] = dlg.getInfo()
            print self.dialogDict['mapinfo']
            if self.dialogDict['mapinfo']['isInfo']:
                if not id:
                    id = wx.NewId()
                    self.canvas.itemType[id] = 'mapinfo'
                    self.canvas.objectId.append(id)
                drawRectangle = self.canvas.CanvasPaperCoordinates(rect = self.dialogDict['mapinfo']['rect'], canvasToPaper = False)
                self.canvas.Draw( pen = self.pen[self.canvas.itemType[id]], brush = self.brush[self.canvas.itemType[id]],
                                pdc = self.canvas.pdcObj, drawid = id, pdctype = 'rect', bb = drawRectangle)
                self.canvas.pdcTmp.RemoveAll()
                self.canvas.dragId = -1
            else: 
                if id:
                    self.deleteObject(id)
                    self.canvas.pdcTmp.RemoveAll()
                    self.canvas.dragId = -1
        dlg.Destroy()
            
    def OnDelete(self, event):
        if self.canvas.dragId != -1:
            self.deleteObject(self.canvas.dragId)
    
    def deleteObject(self, id):
        self.canvas.pdcObj.RemoveId(id)
        self.canvas.pdcTmp.RemoveAll()
        self.canvas.Refresh()
        self.SetDefault(type = self.canvas.itemType[id])
        del self.canvas.itemType[id]
        self.canvas.objectId.remove(id) 
               
    def OnCloseWindow(self, event):
        """!Close window"""
        self.Destroy()

    def find_key(self, dic, val):
        """!Return the key of dictionary given the value"""
        return [k for k, v in dic.iteritems() if v == val]

class PsMapBufferedWindow(wx.Window):
    """!A buffered window class.
    
    @param parent parent window
    @param kwargs other wx.Window parameters
    """
    def __init__(self, parent, id =  wx.ID_ANY,
                 style = wx.NO_FULL_REPAINT_ON_RESIZE,
                 **kwargs):
        wx.Window.__init__(self, parent, id = id, style = style)
        self.parent = parent
    
        self.FitInside()
        
        # store an off screen empty bitmap for saving to file
        self._buffer = None
        # indicates whether or not a resize event has taken place
        self.resize = False 
        

        self.mouse = kwargs['mouse']
        self.pen = kwargs['pen']
        self.brush = kwargs['brush']
        self.cursors = kwargs['cursors']
        self.dialogDict = kwargs['settings']
        # define PseudoDC
        self.pdcObj = wx.PseudoDC()
        self.pdcPaper = wx.PseudoDC()
        self.pdcTmp = wx.PseudoDC()
        
        self.SetClientSize((700,510))#?
        self._buffer = wx.EmptyBitmap(*self.GetClientSize())
        
        self.pageId = []
        self.idBoxTmp = wx.NewId()
        self.dragId = -1
        self.objectId = []
        self.itemType = {}
 
        self.currScale = None
  
        self.Clear()
        
        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda x: None)
        
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE,  self.OnSize)
        self.Bind(wx.EVT_IDLE,  self.OnIdle)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.OnMouse)


    def Clear(self):
        """!Clear canvas and set paper
        """
        bg = wx.LIGHT_GREY_BRUSH
        self.pdcPaper.BeginDrawing()
        self.pdcPaper.SetBackground(bg)
        self.pdcPaper.Clear()
        self.pdcPaper.EndDrawing()
        
        self.SetPage()
        

    def PageRect(self, pageDict):
        """! Returnes offset and scaled page and margins rectangles"""
        ppi = wx.PaintDC(self).GetPPI()
        cW, cH = self.GetClientSize()
        pW, pH = pageDict['Width']*ppi[0], pageDict['Height']*ppi[1]

        if self.currScale is None:
            self.currScale = min(cW/pW, cH/pH)
        paperRect = wx.Rect()
        pW = pW * self.currScale
        pH = pH * self.currScale
        x = cW/2 - pW/2
        y = cH/2 - pH/2
        paperRect = wx.Rect(x, y, pW, pH)
        #margins
        marginRect = wx.Rect(   x + pageDict['Left']*ppi[0] * self.currScale,
                                y + pageDict['Top']*ppi[1] * self.currScale,
                                pW - pageDict['Left']*ppi[0] * self.currScale - pageDict['Right']*ppi[0] * self.currScale,
                                pH - pageDict['Top']*ppi[1] * self.currScale - pageDict['Bottom']*ppi[1] * self.currScale)
        return paperRect, marginRect
    
    def CanvasPaperCoordinates(self, rect, canvasToPaper = True):
        """!Converts canvas (pixel) -> paper (inch) coordinates and size and vice versa"""
        
        units = UnitConversion(self)
        
        fromU = 'pixel'
        toU = 'inch'
        scale = 1/self.currScale
        pRect = self.pdcPaper.GetIdBounds(self.pageId[0])
        pRectx, pRecty = pRect.x, pRect.y 
        if not canvasToPaper: # paper -> canvas
            fromU = 'inch'
            toU = 'pixel'
            scale = self.currScale
            pRectx = units.convert(value =  - pRect.x/scale, fromUnit = 'pixel', toUnit = 'inch' ) #inch, real, negative
            pRecty = units.convert(value =  - pRect.y/scale, fromUnit = 'pixel', toUnit = 'inch' )

        Width = units.convert(value = rect.width * scale, fromUnit = fromU, toUnit = toU)
        Height = units.convert(value = rect.height * scale, fromUnit = fromU, toUnit = toU)
        X = units.convert(value = (rect.x - pRectx) * scale, fromUnit = fromU, toUnit = toU)
        Y = units.convert(value = (rect.y - pRecty) * scale, fromUnit = fromU, toUnit = toU)
        if canvasToPaper: 
            return Rect(X, Y, Width, Height)
        if not canvasToPaper:
            return wx.Rect(X, Y, Width, Height)
        
        
    def SetPage(self):
        """!Sets and changes page, redraws paper"""
        if len(self.pageId) == 0:
            idPaper = wx.NewId()
            idMargins = wx.NewId()
            self.pageId = [idPaper, idMargins]
            self.itemType[self.pageId[0]] = 'paper'   
            self.itemType[self.pageId[1]] = 'margins' 
        cW, cH = self.GetClientSize()
        rectangles = self.PageRect(pageDict = self.parent.dialogDict['page'])
        for id, rect, type in zip(self.pageId, rectangles, ['paper', 'margins']): 
            self.Draw(pen = self.pen[type], brush = self.brush[type], pdc = self.pdcPaper,
                    pdctype = 'rect', drawid = id, bb = rect)


    def modifyRectangle(self, r):
        """! Recalculates rectangle not to have negative size"""
        if r.GetWidth() < 0:
            r.SetX(r.GetX() + r.GetWidth())
        if r.GetHeight() < 0:
            r.SetY(r.GetY() + r.GetHeight())
        r.SetWidth(abs(r.GetWidth()))
        r.SetHeight(abs(r.GetHeight()))
        return r 
          
            
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
        # draw paper
        self.pdcPaper.DrawToDC(dc)
        # draw to the DC using the calculated clipping rect

        rgn = self.GetUpdateRegion()
        
        self.pdcObj.DrawToDCClipped(dc, rgn.GetBox())
        self.pdcTmp.DrawToDCClipped(dc, rgn.GetBox())
    
    def OnMouse(self, event):
        if event.LeftDown():
            self.mouse['begin'] = event.GetPosition()
            if self.mouse['use'] in ('pan', 'zoomin', 'zoomout', 'addMap'):
                pass
            #select
            if self.mouse['use'] == 'pointer':
                found = self.pdcObj.FindObjects(self.mouse['begin'][0], self.mouse['begin'][1])
                if found:
                    self.dragId = found[0]  
                    selected = self.pdcObj.GetIdBounds(self.dragId).Inflate(3,3)
                    self.Draw(pen = self.pen['select'], brush = self.brush['select'], pdc = self.pdcTmp,
                                drawid = self.idBoxTmp, pdctype = 'rect', bb = selected)
                else:
                    self.dragId = -1
                    self.pdcTmp.RemoveId(self.idBoxTmp)
                    self.Refresh()           
          
                   
        elif event.Dragging() and event.LeftIsDown():
            #draw box
            if self.mouse['use'] in ('zoomin', 'zoomout', 'addMap'):
                self.mouse['end'] = event.GetPosition()
                r = wx.Rect(self.mouse['begin'][0], self.mouse['begin'][1],
                            self.mouse['end'][0]-self.mouse['begin'][0], self.mouse['end'][1]-self.mouse['begin'][1])
                r = self.modifyRectangle(r)
                self.Draw(pen = self.pen['box'], brush = self.brush['box'], pdc = self.pdcTmp, drawid = self.idBoxTmp,
                            pdctype = 'rect', bb = r)
                            
            # panning                
            if self.mouse["use"] == 'pan':
                self.mouse['end'] = event.GetPosition()
                view = self.mouse['begin'][0] - self.mouse['end'][0], self.mouse['begin'][1] - self.mouse['end'][1]
                zoomFactor = 1
                self.Zoom(zoomFactor, view)
                self.mouse['begin'] = event.GetPosition()
                
            #move object
            if self.mouse['use'] == 'pointer' and self.dragId != -1:
                self.mouse['end'] = event.GetPosition()
                dx, dy = self.mouse['end'][0] - self.mouse['begin'][0], self.mouse['end'][1] - self.mouse['begin'][1]
                self.pdcObj.TranslateId(self.dragId, dx, dy)
                self.pdcTmp.TranslateId(self.idBoxTmp, dx, dy)
                self.mouse['begin'] = event.GetPosition()
                self.Refresh()
                
        elif event.LeftUp():
            # zoom in, zoom out
            if self.mouse['use'] in ('zoomin','zoomout'):
                zoomR = self.pdcTmp.GetIdBounds(self.idBoxTmp)
                self.pdcTmp.RemoveId(self.idBoxTmp)
                self.Refresh()
                zoomFactor, view = self.ComputeZoom(zoomR)
                self.Zoom(zoomFactor, view)
                self.dragId = -1
                
            # draw map frame    
            if self.mouse['use'] == 'addMap':
                rectTmp = self.pdcTmp.GetIdBounds(self.idBoxTmp)
                rectPaper = self.CanvasPaperCoordinates(rect = rectTmp, canvasToPaper = True)                
                self.dialogDict['map']['rect'] = rectPaper 

                dlg = MapDialog(parent = self, settings = self.dialogDict)
                val = dlg.ShowModal()
                
                if val == wx.ID_OK:
                    self.dialogDict['map'] = dlg.getInfo()
                    rectCanvas = self.CanvasPaperCoordinates(rect = self.dialogDict['map']['rect'],
                                                                canvasToPaper = False)
                    id = wx.NewId()
                    self.itemType[id] = 'map'
                    self.pdcTmp.RemoveId(self.idBoxTmp)
                    self.Draw(pen = self.pen[self.itemType[id]], brush = self.brush[self.itemType[id]], pdc = self.pdcObj,
                                                drawid = id, pdctype = 'rect', bb = rectCanvas)
                    self.objectId.append(id)
                    self.mouse['use'] = self.parent.mouseOld
                    self.SetCursor(self.parent.cursorOld)
                    self.parent.toolbar.ToggleTool(self.parent.actionOld, True)
                    self.parent.toolbar.ToggleTool(self.parent.toolbar.action['id'], False)
                    self.parent.toolbar.action['id'] = self.parent.actionOld
                    
                else:# cancel
                    self.dialogDict['map']['rect'] = None 
                    self.pdcTmp.RemoveId(self.idBoxTmp)
                    self.Refresh() 
                      
                dlg.Destroy()
                self.dragId = -1
            # recalculate the position of objects after dragging    
            if self.mouse['use'] == 'pointer' and self.dragId != -1:
                if self.itemType[self.dragId] == 'map':
                    self.dialogDict['map']['rect'] = self.CanvasPaperCoordinates(rect = self.pdcObj.GetIdBounds(self.dragId),
                                                                canvasToPaper = True)
                if self.itemType[self.dragId] == 'rasterLegend':
                    self.dialogDict['rasterLegend']['where'] = self.CanvasPaperCoordinates(rect = self.pdcObj.GetIdBounds(self.dragId),
                                                                canvasToPaper = True)[:2]

        else:
            pass
##            if self.dragId != -1:
##                vertex = []
##                found = self.pdcObj.FindObjects(*event.GetPosition(), radius = 5)
##                if found:
##                    self.dragId = found[0]  
##                    rectangle = self.pdcObj.GetIdBounds(self.dragId)
##                    vertex.append(rectangle.GetTopLeft())
##                    vertex.append(rectangle.GetTopRight())
##                    vertex.append(rectangle.GetBottomRight())
##                    vertex.append(rectangle.GetBottomLeft())
##                if vertex:
##                    if self.onLine(vertex[0], vertex[1], event.GetPosition()) or \
##                        self.onLine(vertex[1], vertex[2], event.GetPosition()) or\
##                        self.onLine(vertex[2], vertex[3], event.GetPosition()) or\
##                        self.onLine(vertex[3], vertex[0], event.GetPosition()):
##                        self.SetCursor(self.cursors['cross']) 
##                    else:
##                        self.SetCursor(self.parent.cursorOld)
##                else:
##                    self.SetCursor(self.parent.cursorOld) 
##    def onLine(self, point1, point2, point):
##        k = (point1.y - point2.y)/(point1.x - point2.x)
##        y = k * point.x + point1.y - point1.x * k
##        print y - point.y
##        if abs(y - point.y) < 10:
##            return True 
##        else:
##            return False 
                
    def ComputeZoom(self, rect):
        """!Computes zoom factor and scroll view"""
        zoomFactor = 1
        cW, cH = self.GetClientSize()
        cW = float(cW)
        if rect.IsEmpty(): # clicked on canvas
            zoomFactor = 2
            if self.mouse['use'] == 'zoomout':
                zoomFactor = 1./zoomFactor
            x,y = self.mouse['begin']
            xView = x - cW/(zoomFactor * 2)
            yView = y - cH/(zoomFactor * 2)

        else:   #dragging    
            rW, rH = float(rect.GetWidth()), float(rect.GetHeight())
            zoomFactor = 1/max(rW/cW, rH/cH)
            if self.mouse['use'] == 'zoomout':
                zoomFactor = min(rW/cW, rH/cH) 
            if rW/rH > cW/cH:
                yView = rect.GetY() - (rW*(cH/cW) - rH)/2
                xView = rect.GetX()
                
                if self.mouse['use'] == 'zoomout':
                    x,y = rect.GetX() + (rW-(cW/cH)*rH)/2, rect.GetY()
                    xView, yView = -x, -y
            else:
                xView = rect.GetX() - (rH*(cW/cH) - rW)/2
                yView = rect.GetY()
                if self.mouse['use'] == 'zoomout':
                    x,y = rect.GetX(), rect.GetY() + (rH-(cH/cW)*rW)/2
                    xView, yView = -x, -y
        return zoomFactor, (xView, yView)
               
                
    def Zoom(self, zoomFactor, view):
        """! Zoom to specified region, scroll view, redraw"""
        self.currScale = self.currScale*zoomFactor
        if self.currScale > 10 or self.currScale < 0.2:
            self.currScale = self.currScale/zoomFactor
            return 

        # redraw paper
        for i, id in enumerate(self.pageId):
            pRect = self.pdcPaper.GetIdBounds(self.pageId[i])
            pRect.OffsetXY(-view[0], -view[1])
            pRect = self.ScaleRect(rect = pRect, scale = zoomFactor)
            type = self.itemType[id]
            self.Draw(pen = self.pen[type], brush = self.brush[type], pdc = self.pdcPaper,
                        drawid = id, pdctype = 'rect', bb = pRect)

        
        #redraw objects
        for i, id in enumerate(self.objectId):
            oRect = self.pdcObj.GetIdBounds(id)
            oRect.OffsetXY(-view[0] , -view[1])
            oRect = self.ScaleRect(rect = oRect, scale = zoomFactor)
            type = self.itemType[id]
            self.Draw(pen = self.pen[type], brush = self.brush[type], pdc = self.pdcObj,
                        drawid = id, pdctype = 'rect', bb = oRect)
        #redraw tmp objects
        for i, id in enumerate([self.idBoxTmp]):
            oRect = self.pdcTmp.GetIdBounds(id)
            oRect.OffsetXY(-view[0] , -view[1])
            oRect = self.ScaleRect(rect = oRect, scale = zoomFactor)
            type = 'select'
            self.Draw(pen = self.pen[type], brush = self.brush[type], pdc = self.pdcTmp,
                        drawid = id, pdctype = 'rect', bb = oRect)
        
    def ZoomAll(self):
        """! Zoom to full extent"""  
        zoomP = self.pdcPaper.GetIdBounds(self.pageId[0])
        zoomFactor, view = self.ComputeZoom(zoomP)
        self.Zoom(zoomFactor, view)
                    
    def Draw(self, pen, brush, pdc, drawid = None, pdctype = 'rect', bb = wx.Rect(0,0,0,0)): 
        """! Draw object"""    
        if drawid is None:
            drawid = wx.NewId()
            
        pdc.BeginDrawing()
        pdc.RemoveId(drawid)
        pdc.SetId(drawid)
        pdc.SetPen(pen)
        pdc.SetBrush(brush)
        if pdctype == 'rect':
            pdc.DrawRectangleRect(bb)
        pdc.SetIdBounds(drawid, bb)
        self.Refresh()
        pdc.EndDrawing()

        return drawid
    
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

            
    def ScaleRect(self, rect, scale):
        """! Scale rectangle"""
        return wx.Rect(rect.GetX()*scale, rect.GetY()*scale,
                    rect.GetWidth()*scale, rect.GetHeight()*scale)   
                     
def main():
    app = wx.PySimpleApp()
    wx.InitAllImageHandlers()
    frame = PsMapFrame()
    frame.Show()
    
    app.MainLoop()

if __name__ == "__main__":
    main()
