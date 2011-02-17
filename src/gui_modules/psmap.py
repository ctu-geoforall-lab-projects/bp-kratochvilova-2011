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
from math import ceil, sin, cos, pi
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
        self.addVector = wx.NewId()
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
            (self.addVector, 'add vect', Icons['addvect'].GetBitmap(),
             wx.ITEM_NORMAL, "Vector map", "Add vector layer",
             self.parent.OnAddVect),
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
            
        self.itemType = {}
        self.dialogDict = {}
        self.objectId = []
        self.pageId = (wx.NewId(), wx.NewId()) 
        self.SetDefault(id = self.pageId, type = 'page')
        self.canvas = PsMapBufferedWindow(parent = self, mouse = self.mouse, pen = self.pen,
                                            brush = self.brush, cursors = self.cursors, settings = self.dialogDict,
                                            itemType = self.itemType, pageId = self.pageId, objectId = self.objectId)
        self.canvas.SetCursor(self.cursors["default"])
        self.getInitMap()
        
        # save current region
        grass.use_temp_region()
        
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
                                                width = 0, height = 0, cols = 1, font = "Serif", fontsize = 10,
                                                color = 'black', tickbar = False, range = False, min = 0, max = 0,
                                                nodata = False)
        #mapinfo
        self.defaultDict['mapinfo'] = dict(isInfo = False, unit = 'inch', where = (page['Left'], page['Top']),
                                            font = 'Sans', fontsize = 10, color = 'black', background = 'none', 
                                            border = 'none')
        #text
        self.defaultDict['text'] = dict(text = "", font = "Serif", fontsize = 10, color = 'black', background = 'none',
                                        hcolor = 'none', hwidth = 1, border = 'none', width = '1', XY = True,
                                        where = (page['Left'], page['Top']), unit = 'inch', rotate = None, 
                                        ref = "center center", xoffset = 0, yoffset = 0, east = None, north = None)
        #vector
        self.defaultDict['vector'] = dict(list = None)
        
    def SetDefault(self, id, type):
        """!Set default values"""
        self.DefaultData()
        self.dialogDict[id] = self.defaultDict[type]
            
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
        mapId = find_key(dic = self.itemType, val = 'map', multiple = False)
        
        mapinfoId = find_key(dic = self.itemType, val = 'mapinfo', multiple = False)
        
        rasterLegendId = find_key(dic = self.itemType, val = 'rasterLegend', multiple = False)

        vectorId = find_key(dic = self.itemType, val = 'vector', multiple = False)
        
        #change region
        if mapId and self.dialogDict[mapId]['scaleType'] == 1: #fixed scale
            region = grass.region()
            comment = "# set region: g.region n={n} s={s} e={e} w={w}".format(**region)
            instruction.append(comment)
        # paper
        if self.dialogDict[self.pageId]['Format'] == 'custom':
            paperInstruction = "paper\n    width {Width}\n    height {Height}\n".format(**self.dialogDict[self.pageId])
        else:
            paperInstruction = "paper {Format}\n".format(**self.dialogDict[self.pageId])
        paperInstruction += "    left {Left}\n    right {Right}\n"    \
                            "    bottom {Bottom}\n    top {Top}\nend".format(**self.dialogDict[self.pageId])
                        
        instruction.append(paperInstruction)
        # raster
        rasterInstruction = ''
        if mapId and self.dialogDict[mapId]['raster']:
            rasterInstruction = "raster {raster}".format(**self.dialogDict[mapId])
        instruction.append(rasterInstruction)
        #maploc
        if mapId and self.dialogDict[mapId]['rect'] is not None:
            maplocInstruction = "maploc {rect.x} {rect.y}".format(**self.dialogDict[mapId])
            if self.dialogDict[mapId]['scaleType'] != 1:
                maplocInstruction += "  {rect.width} {rect.height}".format(**self.dialogDict[mapId])
            instruction.append(maplocInstruction)
        
        #scale
        if mapId and self.dialogDict[mapId]['scaleType'] == 1: #fixed scale
            scaleInstruction = "scale 1:{0:.0f}".format(1/self.dialogDict[mapId]['scale'])
            instruction.append(scaleInstruction)
        #colortable
        if rasterLegendId:
            rLegendInstruction = "colortable y\n"
            rLegendInstruction += "    raster {raster}\n".format(**self.dialogDict[rasterLegendId])
            rLegendInstruction += "    where {where[0]} {where[1]}\n".format(**self.dialogDict[rasterLegendId])
            if not self.dialogDict[rasterLegendId]['defaultSize']:
                rLegendInstruction += "    width {width}\n".format(**self.dialogDict[rasterLegendId])
            rLegendInstruction += "    discrete {discrete}\n".format(**self.dialogDict[rasterLegendId])
            if self.dialogDict[rasterLegendId]['discrete'] == 'n':
                if not self.dialogDict[rasterLegendId]['defaultSize']:
                    rLegendInstruction += "    height {height}\n".format(**self.dialogDict[rasterLegendId])
                rLegendInstruction += "    tickbar {tickbar}\n".format(**self.dialogDict[rasterLegendId])
                if self.dialogDict[rasterLegendId]['range']:
                    rLegendInstruction += "    range {min} {max}\n".format(**self.dialogDict[rasterLegendId])
            else:
                rLegendInstruction += "    cols {cols}\n".format(**self.dialogDict[rasterLegendId])
                rLegendInstruction += "    nodata {nodata}\n".format(**self.dialogDict[rasterLegendId])
            rLegendInstruction += "    font {font}\n    fontsize {fontsize}\n    color {color}\n"\
                                    .format(**self.dialogDict[rasterLegendId])
            rLegendInstruction += "end"
            instruction.append(rLegendInstruction)
        # mapinfo
        if mapinfoId:
            mapinfoInstruction = "mapinfo\n"
            mapinfoInstruction += "where {where[0]} {where[1]}\n".format(**self.dialogDict['mapinfo'])
            mapinfoInstruction += "font {font}\nfontsize {fontsize}\ncolor {color}\n".format(**self.dialogDict['mapinfo'])            
            mapinfoInstruction += "background {background}\nborder {border}\n".format(**self.dialogDict['mapinfo'])  
            mapinfoInstruction += "end"
            instruction.append(mapinfoInstruction) 
        # text
        textIds = find_key(dic = self.itemType, val = 'text', multiple = True)
        numberOfTexts = len(textIds) if textIds else 0
        for i in range(numberOfTexts):
            i += 1000
            text = self.dialogDict[i]['text'].replace('\n','\\n')
            textInstruction = "text {east} {north}".format(**self.dialogDict[i])
            textInstruction += " {0}\n".format(text)
            textInstruction += "    font {font}\n    fontsize {fontsize}\n    color {color}\n".format(**self.dialogDict[i])
            textInstruction += "    hcolor {hcolor}\n".format(**self.dialogDict[i])
            if self.dialogDict[i]['hcolor'] != 'none':
                textInstruction += "    hwidth {hwidth}\n".format(**self.dialogDict[i])
            textInstruction += "    border {border}\n".format(**self.dialogDict[i])
            if self.dialogDict[i]['border'] != 'none':
                textInstruction += "    width {width}\n".format(**self.dialogDict[i])
            textInstruction += "    background {background}\n".format(**self.dialogDict[i])
            if self.dialogDict[i]["ref"] != '0':
                textInstruction += "    ref {ref}\n".format(**self.dialogDict[i])
            if self.dialogDict[i]["rotate"]:
                textInstruction += "    rotate {rotate}\n".format(**self.dialogDict[i])
            if float(self.dialogDict[i]["xoffset"]) or float(self.dialogDict[i]["yoffset"]):
                textInstruction += "    xoffset {xoffset}\n    yoffset {yoffset}\n".format(**self.dialogDict[i])
            textInstruction += "end"
            instruction.append(textInstruction) 
            
        #vector maps
        if vectorId:
            for map in self.dialogDict[vectorId]['list']:
                dic = self.dialogDict[map[2]]
                if map[1] == 'points':
                    vpointsInstruction = "vpoints {0}\n".format(map[0])
                    
                    if any(dic['type']):
                        vpointsInstruction += "    type {type}\n".format(**dic)
                    if dic['connection']:
                        vpointsInstruction += "    layer {layer}\n".format(**dic)
                        if dic.has_key('cats'):
                            vpointsInstruction += "    cats {cats}\n".format(**dic)
                        elif dic.has_key('where'):
                            vpointsInstruction += "    where {where}\n".format(**dic)
                    vpointsInstruction += "    masked {masked}\n".format(**dic)
                        
                    vpointsInstruction += "end"
                    instruction.append(vpointsInstruction)
                if map[1] == 'lines':
                    vlinesInstruction = "vlines {0}\n".format(map[0])
                    if any(dic['type']):
                        vlinesInstruction += "    type {type}\n".format(**dic)
                    if dic['connection']:
                        vlinesInstruction += "    layer {layer}\n".format(**dic)
                        if dic.has_key('cats'):
                            vlinesInstruction += "    cats {cats}\n".format(**dic)
                        elif dic.has_key('where'):
                            vlinesInstruction += "    where {where}\n".format(**dic)
                    vlinesInstruction += "    masked {masked}\n".format(**dic)
                    vlinesInstruction += "end"
                    instruction.append(vlinesInstruction)
                if map[1] == 'areas':
                    vareasInstruction = "vareas {0}\n".format(map[0])
                    #...
                    vareasInstruction += "end"
                    instruction.append(vareasInstruction)
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
            if self.dialogDict[self.pageId]['Orientation'] == 'Landscape':
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
        
        mapId = find_key(dic = self.dialogDict, val = 'map')
  
        if mapId and self.dialogDict[mapId]['raster']:
            mapName = self.dialogDict[mapId]['raster'].split('@')[0] + suffix[0]
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
        dlg = PageSetupDialog(self, settings = self.dialogDict, itemType = self.itemType) 
        dlg.CenterOnScreen()
        val = dlg.ShowModal()
        if val == wx.ID_OK:
            self.dialogDict[self.pageId] = dlg.getInfo()
            self.canvas.SetPage()
            self.canvas.RecalculatePosition(ids = self.objectId)
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
        if event.GetId() != self.toolbar.action['id']:
            self.actionOld = self.toolbar.action['id']
            self.mouseOld = self.mouse['use']
            self.cursorOld = self.canvas.GetCursor()
        self.toolbar.OnTool(event)
        
        mapId = find_key(dic = self.itemType, val = 'map')

        if mapId: # map exists
            dlg = MapDialog(parent = self, settings = self.dialogDict, itemType = self.itemType)
            val = dlg.ShowModal()
            if val == wx.ID_OK:
                self.dialogDict[mapId] = dlg.getInfo()
                rectCanvas = self.canvas.CanvasPaperCoordinates(rect = self.dialogDict[mapId]['rect'],
                                                                    canvasToPaper = False)
                self.canvas.RecalculateEN()
                self.canvas.pdcTmp.RemoveAll()
                self.canvas.Draw( pen = self.pen[self.itemType[mapId]], brush = self.brush[self.itemType[mapId]],
                                pdc = self.canvas.pdcObj, drawid = mapId, pdctype = 'rect', bb = rectCanvas)
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
            
    def OnAddVect(self, event):
        id = find_key(self.itemType, 'vector')
        isNew = False
        if not id:
            id = self.createObject(type = 'vector', drawable = False)
            isNew = True
        dlg = MainVectorDialog(self, settings = self.dialogDict, itemType = self.itemType)
        if dlg.ShowModal() == wx.ID_OK:
            self.dialogDict[id] = dlg.getInfo()
            if len(self.dialogDict[id]['list']) == 0:
                self.deleteObject(id)
        elif isNew:
            self.deleteObject(id)
        dlg.Destroy()
        
    def OnDecoration(self, event):
        """!Decorations overlay menu
        """
        decmenu = wx.Menu()
        # legend
        AddLegend = wx.MenuItem(decmenu, wx.ID_ANY, "Show legend")##
        AddLegend.SetBitmap(Icons["addlegend"].GetBitmap(self.iconsize))
        decmenu.AppendItem(AddLegend)
        self.Bind(wx.EVT_MENU, self.OnAddLegend, AddLegend)
        # mapinfo
        AddMapinfo = wx.MenuItem(decmenu, wx.ID_ANY, "Show mapinfo")
        AddMapinfo.SetBitmap(Icons["addlegend"].GetBitmap(self.iconsize))
        decmenu.AppendItem(AddMapinfo)
        self.Bind(wx.EVT_MENU, self.OnAddMapinfo, AddMapinfo) 
        # text
        AddText = wx.MenuItem(decmenu, wx.ID_ANY, "Add text")
        AddText.SetBitmap(Icons["addtext"].GetBitmap(self.iconsize))
        decmenu.AppendItem(AddText)
        self.Bind(wx.EVT_MENU, self.OnAddText, AddText) 
        # Popup the menu.  If an item is selected then its handler
        # will be called before PopupMenu returns.
        self.PopupMenu(decmenu)
        decmenu.Destroy()
        
    def OnAddLegend(self, event):
        id = find_key(dic = self.itemType, val = 'rasterLegend')
        if not id:
            id = self.createObject(type = 'rasterLegend')
        dlg = LegendDialog(self, settings = self.dialogDict, itemType = self.itemType)
        if dlg.ShowModal() == wx.ID_OK:
            self.dialogDict[id] = dlg.getInfo()
            if self.dialogDict[id]['rLegend']:
                drawRectangle = self.canvas.CanvasPaperCoordinates(rect = self.dialogDict[id]['rect'], canvasToPaper = False)
                self.canvas.Draw( pen = self.pen[self.itemType[id]], brush = self.brush[self.itemType[id]],
                                pdc = self.canvas.pdcObj, drawid = id, pdctype = 'rect', bb = drawRectangle)
                self.canvas.pdcTmp.RemoveAll()
                self.canvas.dragId = -1
            else: 
                self.deleteObject(id)
                self.canvas.pdcTmp.RemoveAll()
                self.canvas.dragId = -1
        dlg.Destroy()

    def OnAddMapinfo(self, event):
        id = find_key(self.itemType, 'mapinfo')
        if not id:
            id = self.createObject(type = 'mapinfo')
        dlg = MapinfoDialog(self, settings = self.dialogDict, itemType = self.itemType)
        if dlg.ShowModal() == wx.ID_OK:
            self.dialogDict[id] = dlg.getInfo()
            if self.dialogDict[id]['isInfo']:
                drawRectangle = self.canvas.CanvasPaperCoordinates(rect = self.dialogDict[id]['rect'], canvasToPaper = False)
                self.canvas.Draw( pen = self.pen[self.itemType[id]], brush = self.brush[self.itemType[id]],
                                pdc = self.canvas.pdcObj, drawid = id, pdctype = 'rect', bb = drawRectangle)
                self.canvas.pdcTmp.RemoveAll()
                self.canvas.dragId = -1
            else: 
                self.deleteObject(id)
                self.canvas.pdcTmp.RemoveAll()
                self.canvas.dragId = -1
        dlg.Destroy()
        
    def OnAddText(self, event, id = None):
        if id is None:
            id = find_key(dic = self.itemType, val = 'text', multiple = True)
            #no text yet -> new id, if text -> last id + 1 
            id = id[-1] + 1 if id else 1000
            self.createObject(type = 'text', id = id)
        dlg = TextDialog(self, settings = self.dialogDict, itemType = self.itemType, textId = id) 
        if dlg.ShowModal() == wx.ID_OK:
            self.dialogDict[id] = dlg.getInfo()
            rot = float(self.dialogDict[id]['rotate']) if self.dialogDict[id]['rotate'] else 0
            
            extent = self.getTextExtent(textDict = self.dialogDict[id])
            rect = Rect(self.dialogDict[id]['where'][0], self.dialogDict[id]['where'][1], 0, 0)
            self.dialogDict[id]['coords'] = list(self.canvas.CanvasPaperCoordinates(rect = rect, canvasToPaper = False)[:2])
            if self.dialogDict[id]['ref'].split()[0] == 'lower':
                self.dialogDict[id]['coords'][1] -= extent[1]
            elif self.dialogDict[id]['ref'].split()[0] == 'center':
                self.dialogDict[id]['coords'][1] -= extent[1]/2
            if self.dialogDict[id]['ref'].split()[1] == 'right':
                self.dialogDict[id]['coords'][0] -= extent[0] * cos(rot/180*pi)
                self.dialogDict[id]['coords'][1] += extent[0] * sin(rot/180*pi)
            elif self.dialogDict[id]['ref'].split()[1] == 'center':
                self.dialogDict[id]['coords'][0] -= extent[0]/2 * cos(rot/180*pi)
                self.dialogDict[id]['coords'][1] += extent[0]/2 * sin(rot/180*pi)
                
            self.dialogDict[id]['coords'][0] += self.dialogDict[id]['xoffset']
            self.dialogDict[id]['coords'][1] += self.dialogDict[id]['yoffset']
            coords = self.dialogDict[id]['coords']
            bounds = self.getModifiedTextBounds(coords[0], coords[1], extent, rot)
            self.canvas.DrawRotText(pdc = self.canvas.pdcObj, drawId = id, textDict = self.dialogDict[id],
                                        coords = coords, bounds = bounds)
            self.canvas.pdcTmp.RemoveAll()
            self.canvas.dragId = -1

        else:
            if event is not None:
                self.deleteObject(id)
        dlg.Destroy()
        
    def getModifiedTextBounds(self, x, y, textExtent, rotation):
        """!computes bounding box of rotated text, not very precisely"""
        w, h = textExtent
        rotation = float(rotation)/180*pi
        H = float(w) * sin(rotation)
        W = float(w) * cos(rotation)
        X, Y = x, y
        if pi/2 < rotation <= 3*pi/2:
            X = x + W 
        if 0 < rotation < pi:
            Y = y - H
        return wx.Rect(X, Y, abs(W), abs(H)).Inflate(h,h) 
       
    def getTextExtent(self, textDict):
        fontsize = str(textDict['fontsize'] * self.canvas.currScale)
        #fontsize = str(fontsize if fontsize >= 4 else 4)
        dc = wx.PaintDC(self) # dc created because of method GetTextExtent, which pseudoDC lacks
        dc.SetFont(wx.FontFromNativeInfoString(textDict['font'] + " " + fontsize))
        print dc.GetFont().GetNativeFontInfo()
        return dc.GetTextExtent(textDict['text'])
    
    def getInitMap(self):
        """!Create default map frame when no map is selected, needed for coordinates in map units"""
        tmpFile = tempfile.NamedTemporaryFile(mode = 'w')
        tmpFile.file.write(self.InstructionFile())
        tmpFile.file.flush()
        bb = map(float, RunCommand('ps.map', read = True, flags = 'b', input = tmpFile.name, 
                                            output = 'foo').strip().split('=')[1].split(','))
        mapInitRect = rect = Rect(bb[0], bb[3], bb[2] - bb[0], bb[1] - bb[3])    

        region = grass.region()
        units = UnitConversion(self)
        realWidth = units.convert(value = abs(region['w'] - region['e']), fromUnit = 'meter', toUnit = 'inch')
        scale = (bb[2] - bb[0])/realWidth  
        id = wx.NewId()
        self.itemType[id] = 'initMap'                                                                                    
        self.dialogDict[id] = {'rect': mapInitRect, 'scale': scale}

    def OnDelete(self, event):
        if self.canvas.dragId != -1:
            if self.itemType[self.canvas.dragId] == 'map':
                self.deleteObject(self.canvas.dragId)
                originRegionName = os.environ['WIND_OVERRIDE']
                RunCommand('g.region', region = originRegionName)
                self.getInitMap()
                self.canvas.RecalculateEN()
            else:
                self.deleteObject(self.canvas.dragId)
            self.canvas.dragId = -1
    
    def deleteObject(self, id):
        """!Deletes object, his id and redraws"""
        self.canvas.pdcObj.RemoveId(id)
        self.canvas.pdcTmp.RemoveAll()
        self.canvas.Refresh()
        del self.itemType[id]
        del self.dialogDict[id]
        self.objectId.remove(id) if id in self.objectId else None
        
    def createObject(self, type, id = None, drawable = True):
        if not id:
            id = wx.NewId()
        self.itemType[id] = type
        self.objectId.append(id) if drawable else None
        self.SetDefault(id = id, type = type)
        return id
        
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
        self.itemType = kwargs['itemType']
        self.pageId = kwargs['pageId']
        self.objectId = kwargs['objectId']
        
        # define PseudoDC
        self.pdcObj = wx.PseudoDC()
        self.pdcPaper = wx.PseudoDC()
        self.pdcTmp = wx.PseudoDC()
        
        self.SetClientSize((700,510))#?
        self._buffer = wx.EmptyBitmap(*self.GetClientSize())
        
        self.idBoxTmp = wx.NewId()
        self.dragId = -1
        

 
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
        pRect = self.pdcPaper.GetIdBounds(self.pageId[0])
        pRectx, pRecty = pRect.x, pRect.y 
        scale = 1/self.currScale
        if not canvasToPaper: # paper -> canvas
            fromU = 'inch'
            toU = 'pixel'
            scale = self.currScale
            pRectx = units.convert(value =  - pRect.x, fromUnit = 'pixel', toUnit = 'inch' ) /scale #inch, real, negative
            pRecty = units.convert(value =  - pRect.y, fromUnit = 'pixel', toUnit = 'inch' ) /scale 
        Width = units.convert(value = rect.width, fromUnit = fromU, toUnit = toU) * scale
        Height = units.convert(value = rect.height, fromUnit = fromU, toUnit = toU) * scale
        X = units.convert(value = (rect.x - pRectx), fromUnit = fromU, toUnit = toU) * scale
        Y = units.convert(value = (rect.y - pRecty), fromUnit = fromU, toUnit = toU) * scale
##        if canvasToPaper: 
        return Rect(X, Y, Width, Height)
##        if not canvasToPaper:
##            return Rect(X, Y, Width, Height)
        
        
    def SetPage(self):
        """!Sets and changes page, redraws paper"""
        self.itemType[self.pageId[0]] = 'paper'   
        self.itemType[self.pageId[1]] = 'margins' 
        rectangles = self.PageRect(pageDict = self.dialogDict[self.pageId])
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
          
    def RecalculateEN(self):
        """!Recalculate east and north for texts (eps, points) after their or map's movement"""
        mapId = find_key(dic = self.itemType, val = 'map')
        if mapId is None:
            mapId = find_key(dic = self.itemType, val = 'initMap')
        textIds = find_key(dic = self.itemType, val = 'text', multiple = True)
        for id in textIds:
            e, n = PaperMapCoordinates(self, mapId = mapId, x = self.dialogDict[id]['where'][0],
                                                y = self.dialogDict[id]['where'][1], paperToMap = True)
            self.dialogDict[id]['east'], self.dialogDict[id]['north'] = e, n
            
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
                if self.itemType[self.dragId] == 'text': 
                    self.dialogDict[self.dragId]['coords'] = self.dialogDict[self.dragId]['coords'][0] + dx,\
                                                            self.dialogDict[self.dragId]['coords'][1] + dy
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
                
                mapId = self.parent.createObject(type = 'map')
                self.dialogDict[mapId]['rect'] = rectPaper
                dlg = MapDialog(parent = self, settings = self.dialogDict, itemType = self.itemType)
                val = dlg.ShowModal()
                
                if val == wx.ID_OK:
                    self.dialogDict[mapId] = dlg.getInfo()
                    rectCanvas = self.CanvasPaperCoordinates(rect = self.dialogDict[mapId]['rect'],
                                                                canvasToPaper = False)
                    self.RecalculateEN()
                    self.pdcTmp.RemoveId(self.idBoxTmp)
                    self.Draw(pen = self.pen[self.itemType[mapId]], brush = self.brush[self.itemType[mapId]],
                            pdc = self.pdcObj, drawid = mapId, pdctype = 'rect', bb = rectCanvas)
                    
                    self.mouse['use'] = self.parent.mouseOld
                    self.SetCursor(self.parent.cursorOld)
                    self.parent.toolbar.ToggleTool(self.parent.actionOld, True)
                    self.parent.toolbar.ToggleTool(self.parent.toolbar.action['id'], False)
                    self.parent.toolbar.action['id'] = self.parent.actionOld
                    
                else:# cancel 
                    self.parent.deleteObject(id = mapId)
                    self.pdcTmp.RemoveId(self.idBoxTmp)
                    self.Refresh() 
                      
                dlg.Destroy()
                self.dragId = -1
            
            # recalculate the position of objects after dragging    
            if self.mouse['use'] == 'pointer' and self.dragId != -1:
                self.RecalculatePosition(ids = [self.dragId])
                    
        elif event.LeftDClick():
            if self.dragId != -1:
                if self.itemType[self.dragId] == 'text':
                    self.parent.OnAddText(event = None, id = self.dragId)
                    
                    
                
    def RecalculatePosition(self, ids):
        for id in ids:
            if self.itemType[id] == 'map':
                        self.dialogDict[id]['rect'] = self.CanvasPaperCoordinates(rect = self.pdcObj.GetIdBounds(id),
                                                                    canvasToPaper = True)
                        self.RecalculateEN()
            elif self.itemType[id] == 'rasterLegend':                                               
                self.dialogDict[id]['where'] = self.CanvasPaperCoordinates(rect = self.pdcObj.GetIdBounds(id),
                                                            canvasToPaper = True)[:2]
            elif self.itemType[id] == 'mapinfo':                                               
                self.dialogDict[id]['where'] = self.CanvasPaperCoordinates(rect = self.pdcObj.GetIdBounds(id),
                                                            canvasToPaper = True)[:2]
            elif self.itemType[id] == 'text':
                x, y = self.dialogDict[id]['coords'][0] - self.dialogDict[id]['xoffset'],\
                        self.dialogDict[id]['coords'][1] - self.dialogDict[id]['yoffset']
                extent = self.parent.getTextExtent(textDict = self.dialogDict[id])
                rot = float(self.dialogDict[id]['rotate'])/180*pi if self.dialogDict[id]['rotate']is not None else 0
                if self.dialogDict[id]['ref'].split()[0] == 'lower':
                    y += extent[1]
                elif self.dialogDict[id]['ref'].split()[0] == 'center':
                    y += extent[1]/2
                if self.dialogDict[id]['ref'].split()[1] == 'right':
                    x += extent[0] * cos(rot)
                    y -= extent[0] * sin(rot)
                elif self.dialogDict[id]['ref'].split()[1] == 'center':
                    x += extent[0]/2 * cos(rot)
                    y -= extent[0]/2 * sin(rot)
                
                self.dialogDict[id]['where'] = self.CanvasPaperCoordinates(rect = Rect(x, y, 0, 0),
                                                            canvasToPaper = True)[:2]
                self.RecalculateEN()
        
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
        return zoomFactor, (int(xView), int(yView))
               
                
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
        for id in self.objectId:
            oRect = self.pdcObj.GetIdBounds(id)
            oRect.OffsetXY(-view[0] , -view[1])
            oRect = self.ScaleRect(rect = oRect, scale = zoomFactor)
            type = self.itemType[id]
            if type == 'text':
                coords = self.dialogDict[id]['coords']# recalculate coordinates, they are not equal to BB
                self.dialogDict[id]['coords'] = coords = [(int(coord) - view[i]) * zoomFactor
                                                                    for i, coord in enumerate(coords)]
                self.DrawRotText(pdc = self.pdcObj, drawId = id, textDict = self.dialogDict[id],
                 coords = coords, bounds = oRect )
                extent = self.parent.getTextExtent(textDict = self.dialogDict[id])
                rot = float(self.dialogDict[id]['rotate']) if self.dialogDict[id]['rotate'] else 0
                bounds = self.parent.getModifiedTextBounds(coords[0], coords[1], extent, rot)
                self.pdcObj.SetIdBounds(id, bounds)
            else:
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
        pdc.ClearId(drawid)
        pdc.SetId(drawid)
        pdc.SetPen(pen)
        pdc.SetBrush(brush)
        if pdctype == 'rect':
            pdc.DrawRectangleRect(bb)
        pdc.SetIdBounds(drawid, bb)
        self.Refresh()
        pdc.EndDrawing()

        return drawid
    
    def DrawRotText(self, pdc, drawId, textDict, coords, bounds):
        rot = float(textDict['rotate']) if textDict['rotate'] else 0
        fontsize = str(textDict['fontsize'] * self.currScale)
        background = textDict['background'] if textDict['background'] != 'none' else None
        
        dc = wx.PaintDC(self) # dc created because of method GetTextExtent, which pseudoDC lacks
        dc.SetFont(wx.FontFromNativeInfoString(textDict['font'] + " " + fontsize))
        textExtent = dc.GetTextExtent(textDict['text'])
        pdc.BeginDrawing()
        pdc.ClearId(drawId)
        pdc.SetId(drawId)
        # doesn't work
        if background:
            pdc.SetBackground(wx.Brush(background))
            pdc.SetBackgroundMode(wx.SOLID)
        else:
            pdc.SetBackground(wx.TRANSPARENT_BRUSH)
            pdc.SetBackgroundMode(wx.TRANSPARENT)
        pdc.SetFont(wx.FontFromNativeInfoString(textDict['font'] + " " + fontsize))    
        pdc.SetTextForeground(textDict['color'])        
        pdc.DrawRotatedText(textDict['text'], coords[0], coords[1], rot)
        pdc.SetIdBounds(drawId, bounds)
        self.Refresh()
        pdc.EndDrawing()


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
