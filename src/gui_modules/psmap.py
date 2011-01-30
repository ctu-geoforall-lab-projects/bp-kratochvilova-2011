

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

import wx
import wx.lib.scrolledpanel as scrolled

try:
    from agw import flatnotebook as fnb
except ImportError: # if it's not there locally, try the wxPython lib.
    import wx.lib.agw.flatnotebook as fnb


# like wx.Rect but supports float     
Rect = namedtuple('Rect', 'x y width height')


class UnitConversion():
    """! Class for converting units"""
    def __init__(self, parent):
        self.parent = parent
        ppi = wx.PaintDC(self.parent).GetPPI()
        self._unitsPage = {'inch':1.0,
                            'point':72.0,
                            'centimeter':2.54,
                            'milimeter':25.4}
        self._units = { 'pixel': ppi[0],
                        'meter': 0.0254}
        self._units.update(self._unitsPage)

    def getPageUnits(self):
        return self._unitsPage.keys()
    def convert(self, value, fromUnit = None, toUnit = None):
        return float(value)/self._units[fromUnit]*self._units[toUnit]
        
    
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
class PageSetupDialog(wx.Dialog):
    def __init__(self, parent, pageSetupDict):
        wx.Dialog.__init__(self, parent = parent, id = wx.ID_ANY, 
                            title = "Page setup", size = wx.DefaultSize, style = wx.DEFAULT_DIALOG_STYLE)
        
        self.cat = ['Units', 'Format', 'Orientation', 'Width', 'Height', 'Left', 'Right', 'Top', 'Bottom']
        paperString = RunCommand('ps.map', flags = 'p', read = True)
        self.paperTable = self._toList(paperString) 
        self.units = UnitConversion(self)
        self.unitsList = self.units.getPageUnits()
        self.pageSetupDict = pageSetupDict

        self._layout()
        
        if self.pageSetupDict:
            for item in self.cat[:3]:
                self.getCtrl(item).SetSelection(self.getCtrl(item).FindString(self.pageSetupDict[item]))
            for item in self.cat[3:]:
                self.getCtrl(item).SetValue("{0:4.3f}".format(self.pageSetupDict[item]))

       
        if self.getCtrl('Format').GetString(self.getCtrl('Format').GetSelection()) != 'custom':
            self.getCtrl('Width').Disable()
            self.getCtrl('Height').Disable()
        else:
            self.getCtrl('Orientation').Disable()
        # events
        self.getCtrl('Units').Bind(wx.EVT_CHOICE, self.OnChoice)
        self.getCtrl('Format').Bind(wx.EVT_CHOICE, self.OnChoice)
        self.getCtrl('Orientation').Bind(wx.EVT_CHOICE, self.OnChoice)
        self.btnOk.Bind(wx.EVT_BUTTON, self.OnOK)
    
    def getInfo(self):
        return self.pageSetupDict
    
    def _update(self):
        self.pageSetupDict['Units'] = self.getCtrl('Units').GetString(self.getCtrl('Units').GetSelection())
        self.pageSetupDict['Format'] = self.paperTable[self.getCtrl('Format').GetSelection()]['Format']
        self.pageSetupDict['Orientation'] = self.getCtrl('Orientation').GetString(self.getCtrl('Orientation').GetSelection())
        for item in self.cat[3:]:
            self.pageSetupDict[item] = self.units.convert(value = float(self.getCtrl(item).GetValue()),
                                        fromUnit = self.pageSetupDict['Units'], toUnit = 'inch')
            

            
    def OnOK(self, event):
        try:
            self._update()
        except ValueError:
                wx.MessageBox(message = _("Literal is not allowed!"), caption = _('Invalid input'),
                                    style = wx.OK|wx.ICON_ERROR)
        else:
            event.Skip()
        
    def _layout(self):
        size = (110,-1)
        #sizers
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        pageBox = wx.StaticBox(self, id = wx.ID_ANY, label ="  Page size ")
        pageSizer = wx.StaticBoxSizer(pageBox, wx.VERTICAL)
        marginBox = wx.StaticBox(self, id = wx.ID_ANY, label = " Margins ")
        marginSizer = wx.StaticBoxSizer(marginBox, wx.VERTICAL)
        horSizer = wx.BoxSizer(wx.HORIZONTAL) 
        #staticText + choice
        choices = [self.unitsList, [item['Format'] for item in self.paperTable], ['Portrait', 'Landscape']]
        propor = [0,1,1]
        border = [5,3,3]
        self.hBoxDict={}
        for i, item in enumerate(self.cat[:3]):
            hBox = wx.BoxSizer(wx.HORIZONTAL)
            stText = wx.StaticText(self, id = wx.ID_ANY, label = item + ':')
            choice = wx.Choice(self, id = wx.ID_ANY, choices = choices[i], size = size)
            hBox.Add(stText, proportion = propor[i], flag = wx.ALIGN_CENTER_VERTICAL|wx.ALL, border = border[i])
            hBox.Add(choice, proportion = 0, flag = wx.ALL, border = border[i])
            if item == 'Units':
                hBox.Add(size,1) 
            self.hBoxDict[item] = hBox    

        #staticText + TextCtrl
        for item in self.cat[3:]:
            hBox = wx.BoxSizer(wx.HORIZONTAL)
            label = wx.StaticText(self, id = wx.ID_ANY, label = item + ':')
            textctrl = wx.TextCtrl(self, id = wx.ID_ANY, size = size, value = '')
            hBox.Add(label, proportion = 1, flag = wx.ALIGN_CENTER_VERTICAL|wx.ALL, border = 3)
            hBox.Add(textctrl, proportion = 0, flag = wx.ALIGN_CENTRE|wx.ALL, border = 3)
            self.hBoxDict[item] = hBox
         
        sizer = list([mainSizer] + [pageSizer]*4 + [marginSizer]*4)
        for i, item in enumerate(self.cat):
                sizer[i].Add(self.hBoxDict[item], 0, wx.GROW|wx.RIGHT|wx.LEFT,5)
        # OK button
        btnSizer = wx.StdDialogButtonSizer()
        self.btnOk = wx.Button(self, wx.ID_OK)
        self.btnOk.SetDefault()
        btnSizer.AddButton(self.btnOk)
        btn = wx.Button(self, wx.ID_CANCEL)
        btnSizer.AddButton(btn)
        btnSizer.Realize()
    
    
        horSizer.Add(pageSizer, proportion = 0, flag = wx.LEFT|wx.RIGHT|wx.BOTTOM, border = 10)
        horSizer.Add(marginSizer, proportion = 0, flag = wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND, border = 10)
        mainSizer.Add(horSizer, proportion = 0, border = 10)  
        mainSizer.Add(btnSizer, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.ALL,  border = 10)      
        self.SetSizer(mainSizer)
        mainSizer.Fit(self)
    
    def OnChoice(self, event):
        currPaper = self.paperTable[self.getCtrl('Format').GetSelection()]
        currUnit = self.getCtrl('Units').GetString(self.getCtrl('Units').GetSelection())
        currOrient = self.getCtrl('Orientation').GetString(self.getCtrl('Orientation').GetSelection())
        newSize = dict()
        for item in self.cat[3:]:
            newSize[item] = self.units.convert(float(currPaper[item]), fromUnit = 'inch', toUnit = currUnit)

        enable = True
        if currPaper['Format'] != 'custom':
            if currOrient == 'Landscape':
                newSize['Width'], newSize['Height'] = newSize['Height'], newSize['Width']
            for item in self.cat[3:]:
                self.getCtrl(item).ChangeValue("{0:4.3f}".format(newSize[item]))
            enable = False
        self.getCtrl('Width').Enable(enable)
        self.getCtrl('Height').Enable(enable)
        self.getCtrl('Orientation').Enable(not enable)


    def getCtrl(self, item):
         return self.hBoxDict[item].GetItem(1).GetWindow()
        
    def _toList(self, paperStr):
        
        sizeList = list()
        for line in paperStr.strip().split('\n'):
            d = dict(zip([self.cat[1]]+ self.cat[3:],line.split()))
            sizeList.append(d)
        d = {}.fromkeys([self.cat[1]]+ self.cat[3:], 100)
        d.update(Format = 'custom')
        sizeList.append(d)
        return sizeList
    
class MapDialog(wx.Dialog):
    def __init__(self, parent, mapDict = None):
        wx.Dialog.__init__(self, parent = parent, id = wx.ID_ANY, title = "Map settings",
                            size = wx.DefaultSize, style = wx.DEFAULT_DIALOG_STYLE)
        
        self.parent = parent
        self.mapDialogDict = mapDict
        self.mapsets = [grass.gisenv()['MAPSET'],]
        self.scale, self.rectAdjusted = self.AutoAdjust()
        
        self._layout()
        
        
        if self.mapDialogDict['raster']:
            self.select.SetValue(self.mapDialogDict['raster'])
            
        if self.mapDialogDict['scaleType'] is not None: #0 - automatic, 1 - fixed
            self.choice.SetSelection(self.mapDialogDict['scaleType'])
            if self.mapDialogDict['scaleType'] == 0:
                self.textCtrl.SetValue("1 : {0:.0f}".format(1/self.scale))
                self.textCtrl.Disable()
            elif self.mapDialogDict['scaleType'] == 1:
                self.textCtrl.SetValue("1 : {0:.0f}".format(1/self.mapDialogDict['scale']))
                self.textCtrl.Enable()
            
        self.btnOk.Bind(wx.EVT_BUTTON, self.OnOK)
        
    def AutoAdjust(self):
        grass.del_temp_region()
        currRegionDict = grass.region()
            
        units = UnitConversion(self)
        rX = self.mapDialogDict['rect'].x
        rY = self.mapDialogDict['rect'].y
        rW = self.mapDialogDict['rect'].width
        rH = self.mapDialogDict['rect'].height
        
        mW = units.convert(value = currRegionDict['e'] - currRegionDict['w'], fromUnit = 'meter', toUnit = 'inch')
        mH = units.convert(value = currRegionDict['n'] - currRegionDict['s'], fromUnit = 'meter', toUnit = 'inch')
        scale = min(rW/mW, rH/mH)

        if rW/rH > mW/mH:
            x = rX - (rH*(mW/mH) - rW)/2
            y = rY
            rWNew = rH*(mW/mH)
            rHNew = rH
        else:
            x = rX
            y = rY - (rW*(mH/mW) - rH)/2
            rHNew = rW*(mH/mW)
            rWNew = rW
        return scale, (x, y, rWNew, rHNew) #inch
        
    def _layout(self):
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        
        hBox = wx.BoxSizer(wx.HORIZONTAL)
        text = wx.StaticText(self, id = wx.ID_ANY, label = "Choose raster map: ")
        self.select = Select(self, id = wx.ID_ANY,# size = globalvar.DIALOG_GSELECT_SIZE,
                 type = 'raster', multiple = False, mapsets = self.mapsets,
                 updateOnPopup = True, onPopup = None)
        hBox.Add(text, proportion = 1, flag = wx.ALIGN_CENTER_VERTICAL|wx.ALL, border = 3)
        hBox.Add(self.select, proportion = 0, flag = wx.ALIGN_CENTRE|wx.ALL, border = 3)
        mainSizer.Add(hBox, proportion = 0, flag = wx.GROW|wx.ALL, border = 10)
        
        hBox = wx.BoxSizer(wx.HORIZONTAL)
        text = wx.StaticText(self, id = wx.ID_ANY, label = "Scale: ")
        self.choice = wx.Choice(self, id = wx.ID_ANY, choices = ['Automatic', 'Fixed'])
        self.textCtrl = wx.TextCtrl(self, id = wx.ID_ANY, value = '1:10000', style = wx.TE_RIGHT)
        hBox.Add(text, proportion = 1, flag = wx.ALIGN_CENTER_VERTICAL|wx.ALL, border = 3)
        hBox.Add(self.choice, proportion = 1, flag = wx.ALIGN_CENTRE|wx.ALL, border = 3)
        hBox.Add(self.textCtrl, proportion = 1, flag = wx.ALIGN_CENTRE|wx.ALL, border = 3)
        mainSizer.Add(hBox, proportion = 0, flag = wx.GROW|wx.ALL, border = 10)
        
        #button OK
        btnSizer = wx.StdDialogButtonSizer()
        self.btnOk = wx.Button(self, wx.ID_OK)
        self.btnOk.SetDefault()
        btnSizer.AddButton(self.btnOk)
        btn = wx.Button(self, wx.ID_CANCEL)
        btnSizer.AddButton(btn)
        btnSizer.Realize()
        
        
         
        mainSizer.Add(btnSizer, proportion = 0, flag = wx.GROW|wx.ALL, border = 10)
        self.SetSizer(mainSizer)
        mainSizer.Fit(self)
    
        self.choice.Bind(wx.EVT_CHOICE, self.OnScaleChoice)
        
    def OnScaleChoice(self, event):
        scaleType = self.choice.GetSelection()
        if scaleType == 0: # automatic
            self.textCtrl.Disable()
            self.textCtrl.SetValue("1 : {0:.0f}".format(1/self.scale))
        elif scaleType == 1:
            self.textCtrl.Enable()
           
            
    def _update(self):
        units = UnitConversion(self)
        #raster
        self.mapDialogDict['raster'] = self.select.GetValue() 
        #scale
        scaleType = self.choice.GetSelection()
        if scaleType == 0: # automatic
            self.scale, self.rectAdjusted = self.AutoAdjust()
            self.mapDialogDict['rect'] = Rect(*self.rectAdjusted) 
            self.mapDialogDict['scaleType'] = 0
            self.mapDialogDict['scale'] = self.scale            
        elif scaleType == 1:
            self.mapDialogDict['scaleType'] = 1
            scaleNumber = float(self.textCtrl.GetValue().split(':')[1].strip())
            self.mapDialogDict['scale'] = 1/scaleNumber
            
            rectHalfInch = ( self.mapDialogDict['rect'].width/2, self.mapDialogDict['rect'].height/2)
            rectHalfMeter = ( units.convert(value = rectHalfInch[0], fromUnit = 'inch', toUnit = 'meter')*scaleNumber,
                                units.convert(value = rectHalfInch[1], fromUnit = 'inch', toUnit = 'meter')*scaleNumber) 
            currRegCentre = RunCommand('g.region', read = True, flags = 'c')
            currRegCentreDict = {}
            for item in currRegCentre.strip().split('\n'):
                currRegCentreDict[item.split(':')[0].strip()] = float(item.split(':')[1].strip())
                
            grass.use_temp_region()
            RunCommand('g.region',  n = currRegCentreDict['center northing'] + rectHalfMeter[1],
                                    s = currRegCentreDict['center northing'] - rectHalfMeter[1],
                                    e = currRegCentreDict['center easting'] + rectHalfMeter[0],
                                    w = currRegCentreDict['center easting'] - rectHalfMeter[0])
            

    def getInfo(self):
        return self.mapDialogDict
    
    def OnOK(self, event):
        self._update()
        event.Skip()
  


class LegendDialog(wx.Dialog):
    def __init__(self, parent, legendDict = None):
        wx.Dialog.__init__(self, parent = parent, id = wx.ID_ANY, title = "Legend settings",
                            size = wx.DefaultSize, style = wx.DEFAULT_DIALOG_STYLE)
        self.parent = parent
        self.legendDict = legendDict
        self.mapsets = [grass.gisenv()['MAPSET'],]
        self.units = UnitConversion(self)
        
        # notebook
        notebook = wx.Notebook(parent = self, id = wx.ID_ANY, style = wx.BK_DEFAULT)
        self.panelRaster = self._rasterLegend(notebook)
        self._vectorLegend(notebook)

        # buttons
        btnCancel = wx.Button(self, wx.ID_CANCEL)
        btnOK = wx.Button(self, wx.ID_OK)
        btnOK.SetDefault()

        # bindigs
        btnOK.Bind(wx.EVT_BUTTON, self.OnOK)
        btnOK.SetToolTipString(_("Close dialog and apply changes"))
        btnCancel.Bind(wx.EVT_BUTTON, self.OnCancel)
        btnCancel.SetToolTipString(_("Close dialog and ignore changes"))
        
        # sizers
        btnSizer = wx.StdDialogButtonSizer()
        btnSizer.AddButton(btnCancel)
        btnSizer.AddButton(btnOK)
        btnSizer.Realize()
        
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(item = notebook, proportion = 1, flag = wx.EXPAND | wx.ALL, border = 5)
        mainSizer.Add(item = btnSizer, proportion = 0,
                      flag = wx.EXPAND | wx.ALL | wx.ALIGN_CENTER, border = 5)
        
        self.Bind(wx.EVT_CLOSE, self.OnCancel)
        
        self.SetSizer(mainSizer)
        mainSizer.Fit(self)
        
    def _rasterLegend(self, notebook):
        panel = scrolled.ScrolledPanel(parent = notebook, id = wx.ID_ANY, size = (-1, 500), style = wx.TAB_TRAVERSAL)
        panel.SetupScrolling(scroll_x = False, scroll_y = True)
        notebook.AddPage(page = panel, text = _("Raster legend"))

        border = wx.BoxSizer(wx.VERTICAL)
        # is legend
        self.isLegend = wx.CheckBox(panel, id = wx.ID_ANY, label = _("Add raster legend"))
        self.isLegend.SetValue(True)
        #units
        box = wx.BoxSizer(wx.HORIZONTAL)
        units = wx.StaticText(panel, id = wx.ID_ANY, label = _("Units:"))
        choices = self.units.getPageUnits()
        self.unitsChoice = wx.Choice(panel, id = wx.ID_ANY, choices = choices)
        box.Add(self.isLegend, proportion = 1, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        box.Add(units, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        box.Add(self.unitsChoice, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border = 5)
        border.Add(item = box, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)

        # choose raster
        
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Source raster")))
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        flexSizer = wx.FlexGridSizer (cols = 2, hgap = 5, vgap = 5)
        flexSizer.AddGrowableCol(1)
        
        self.rasterDefault = wx.RadioButton(panel, id = wx.ID_ANY, label = _("current raster"))
        self.rasterOther = wx.RadioButton(panel, id = wx.ID_ANY, label = _("select raster"))
        self.rasterCurrent = wx.StaticText(panel, id = wx.ID_ANY, label = _("{0}").format(self.parent.dialogDict['map']['raster']) )
        self.rasterSelect = Select( panel, id = wx.ID_ANY, size = globalvar.DIALOG_GSELECT_SIZE,
                                type = 'raster', multiple = False, mapsets = self.mapsets,
                                updateOnPopup = True, onPopup = None)
        flexSizer.Add(self.rasterDefault, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        flexSizer.Add(self.rasterCurrent, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border = 0)
        flexSizer.Add(self.rasterOther, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        flexSizer.Add(self.rasterSelect, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border = 0)
        
        sizer.Add(item = flexSizer, proportion = 1, flag = wx.ALL | wx.EXPAND, border = 1)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        # size and position
        
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Size and position")))
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        
        gridBagSizer = wx.GridBagSizer( hgap = 5, vgap = 5)
        #gridBagSizer.AddGrowableCol(1)
        #gridBagSizer.AddGrowableCol(3)
        gridBagSizer.AddGrowableCol(5)
        
        commentPosition = wx.StaticText(panel, id = wx.ID_ANY,\
                    label = _("Position of the top left corner from the top left edge of the paper:"))
        x = wx.StaticText(panel, id = wx.ID_ANY, label = _("X:"))
        y = wx.StaticText(panel, id = wx.ID_ANY, label = _("Y:"))
        self.xCoord = wx.TextCtrl(panel, id = wx.ID_ANY, value = "0")
        self.yCoord = wx.TextCtrl(panel, id = wx.ID_ANY, value = "0")
        
        self.defaultSize = wx.CheckBox(panel, id = wx.ID_ANY, label = _("Use default size"))
        width = wx.StaticText(panel, id = wx.ID_ANY, label = _("Width:"))
        self.widthCtrl = wx.TextCtrl(panel, id = wx.ID_ANY, value = "0")
        height = wx.StaticText(panel, id = wx.ID_ANY, label = _("Height:"))
        self.heightCtrl = wx.TextCtrl(panel, id = wx.ID_ANY, value = "0")
        cols = wx.StaticText(panel, id = wx.ID_ANY, label = _("Columns:"))
        self.colsCtrl = wx.SpinCtrl(panel, id = wx.ID_ANY, value = "", min = 1, max = 10, initial = 1)

        gridBagSizer.Add(commentPosition, pos = (0,0), span = (1,6), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(x, pos = (1,0), flag = wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border = 0)
        gridBagSizer.Add(self.xCoord, pos = (1,1), flag = wx.ALIGN_LEFT, border = 0)
        gridBagSizer.Add(y, pos = (1,2), flag = wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border = 0)
        gridBagSizer.Add(self.yCoord, pos = (1,3), flag = wx.ALIGN_LEFT, border = 0)
        gridBagSizer.Add(self.defaultSize, pos = (2,0), span = (1, 3), flag = wx.ALIGN_LEFT, border = 0)
        gridBagSizer.Add(width, pos = (3,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.widthCtrl, pos = (3,1), flag = wx.ALIGN_LEFT, border = 0)
        gridBagSizer.Add(height, pos = (3,2), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.heightCtrl, pos = (3,3), flag = wx.ALIGN_LEFT, border = 0)
        gridBagSizer.Add(cols, pos = (3,4), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.colsCtrl, pos = (3,5), flag = wx.ALIGN_LEFT, border = 0)
       
        sizer.Add(item = gridBagSizer, proportion = 1, flag = wx.ALL | wx.EXPAND, border = 1)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        # font settings
        
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Font settings")))
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        flexSizer = wx.FlexGridSizer (cols = 5, hgap = 5, vgap = 5)
        flexSizer.AddGrowableCol(1)
        
        font = wx.StaticText(panel, id = wx.ID_ANY, label = _("Font:"))
        fontSize = wx.StaticText(panel, id = wx.ID_ANY, label = _("Font size:"))
        fontSizeUnit = wx.StaticText(panel, id = wx.ID_ANY, label = _("points"))
        color = wx.StaticText(panel, id = wx.ID_ANY, label = _("Color:"))
        fontChoices = [ 'Times-Roman', 'Times-Italic', 'Times-Bold', 'Times-BoldItalic', 'Helvetica',\
                        'Helvetica-Oblique', 'Helvetica-Bold', 'Helvetica-BoldOblique', 'Courier',\
                        'Courier-Oblique', 'Courier-Bold', 'Courier-BoldOblique']
        colorChoices = [  'aqua', 'black', 'blue', 'brown', 'cyan', 'gray', 'green', 'indigo', 'magenta',\
                        'orange', 'purple', 'red', 'violet', 'white', 'yellow']
        self.fontCtrl = wx.Choice(panel, id = wx.ID_ANY, choices = fontChoices)
        self.colorCtrl = wx.Choice(panel, id = wx.ID_ANY, choices = colorChoices)
        self.fontSizeCtrl = wx.SpinCtrl(panel, id = wx.ID_ANY, min = 1, max = 99, initial = 10)
        
        flexSizer.Add(font, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        flexSizer.Add(self.fontCtrl, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL|wx.FIXED_MINSIZE, border = 0)
        flexSizer.Add(fontSize, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        flexSizer.Add(self.fontSizeCtrl, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        flexSizer.Add(fontSizeUnit, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        flexSizer.Add(color, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)        
        flexSizer.Add(self.colorCtrl, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        
        sizer.Add(item = flexSizer, proportion = 1, flag = wx.ALL | wx.EXPAND, border = 1)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        # FCELL settings
        
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Floating point raster settings")))
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        gridBagSizer = wx.GridBagSizer (hgap = 5, vgap = 5)
        #tickbar
        self.ticks = wx.CheckBox(panel, id = wx.ID_ANY, label = _("draw ticks across color table"))
        # range
        self.range = wx.CheckBox(panel, id = wx.ID_ANY, label = _("range"))
        minText =  wx.StaticText(panel, id = wx.ID_ANY, label = _("min:"))
        maxText =  wx.StaticText(panel, id = wx.ID_ANY, label = _("max:"))
        self.min = wx.TextCtrl(panel, id = wx.ID_ANY, value = "0")
        self.max = wx.TextCtrl(panel, id = wx.ID_ANY, value = "0")
        self.discreteFcell = wx.CheckBox(panel, id = wx.ID_ANY, label = _("discrete range bands"))
        
        gridBagSizer.Add(self.discreteFcell, pos = (0,0), span = (1,5), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.ticks, pos = (1,0), span = (1,5), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.range, pos = (2,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(minText, pos = (2,1), flag = wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border = 0)
        gridBagSizer.Add(self.min, pos = (2,2), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(maxText, pos = (2,3), flag = wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border = 0)
        gridBagSizer.Add(self.max, pos = (2,4), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        
        sizer.Add(gridBagSizer, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        #CELL settings
        
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Categorical map settings")))
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        gridBagSizer = wx.GridBagSizer (hgap = 5, vgap = 5)
        # no data
        self.nodata = wx.CheckBox(panel, id = wx.ID_ANY, label = _('do not draw "no data" box'))
        #discrete
        self.discreteCell = wx.CheckBox(panel, id = wx.ID_ANY, label = _("discrete legend"))
        
        gridBagSizer.Add(self.discreteCell, pos = (0,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.nodata, pos = (1,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        
        sizer.Add(gridBagSizer, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        panel.SetSizer(border)
        panel.Fit()
        
        # bindings
        self.Bind(wx.EVT_RADIOBUTTON, self.OnRaster, self.rasterDefault)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnRaster, self.rasterOther)
        self.Bind(wx.EVT_CHECKBOX, self.OnIsLegend, self.isLegend)
        self.Bind(wx.EVT_CHECKBOX, self.OnDefaultSize, self.defaultSize)
        self.Bind(wx.EVT_CHECKBOX, self.OnRange, self.range)
        # no events from gselect!
        
        if not self.parent.dialogDict['map']['raster']:
            self.rasterOther.SetValue(True)
        else:
            self.rasterDefault.SetValue(True)
        self.OnRaster(None)
        
        return panel
    
    def _vectorLegend(self, notebook):
        pass
        
        
    #   some enable/disable methods  
    
    def OnIsLegend(self, event):
        children = self.panelRaster.GetChildren()
        if self.isLegend.GetValue():
            for i,widget in enumerate(children):
                    widget.Enable()
        else:
            for i,widget in enumerate(children):
                if i != 0:
                    widget.Disable()
                    
    def OnRaster(self, event):
        if self.rasterDefault.GetValue():#default
            self.rasterSelect.Disable()
        else:#select raster
            self.rasterSelect.Enable()
            
##    def OnChangeMap(self, event):
##        map = self.rasterSelect.GetValue()
##        rasterType = RunCommand('r.info', flags = 't', read = True, map = map)
##        if not rasterType:
##            return
##        rasterType = rasterType.strip().split('=')[1]
            
    def OnDefaultSize(self, event):
        if self.defaultSize.GetValue():
            self.widthCtrl.Disable()
            self.heightCtrl.Disable()            
        else:    
            self.widthCtrl.Enable()
            self.heightCtrl.Enable()
    
    def OnRange(self, event):
        if not self.range.GetValue():
            self.min.Disable()        
            self.max.Disable()
        else:
            self.min.Enable()        
            self.max.Enable()            
         
           
    def OnOK(self, event):
        self.update()
        if self.legendDict['rLegend']:
            if not self.legendDict['raster']:
                wx.MessageBox(message = _("No raster map selected!"),
                                    caption = _('No raster'), style = wx.OK|wx.ICON_ERROR)
            else:
                event.Skip()
        else:
            event.Skip()
        
    def OnCancel(self, event):
        event.Skip()
    
    def update(self):
        #is raster legend
        if not self.isLegend.GetValue():
            self.legendDict['rLegend'] = False
            return
        else:
            self.legendDict['rLegend'] = True
        #units
        currUnit = self.units.getPageUnits()[self.unitsChoice.GetSelection()]
        self.legendDict['unit'] = currUnit
        # raster
        if self.rasterDefault.GetValue():
            self.legendDict['raster'] = self.parent.dialogDict['map']['raster']
        else:
            self.legendDict['raster'] = self.rasterSelect.GetValue()
            
        if self.legendDict['raster']:
            # type and range of map
            rasterType = RunCommand('r.info', flags = 't', read = True, map = self.legendDict['raster']).strip().split('=')[1]
            self.legendDict['type'] = rasterType
            
            range = RunCommand('r.info', flags = 'r', read = True, map = self.legendDict['raster']).strip().split('\n')
            minim, maxim = range[0].split('=')[1], range[1].split('=')[1]  
            # font 
            self.legendDict['fontsize'] = self.fontSizeCtrl.GetValue()
            self.legendDict['font'] = self.fontCtrl.GetStringSelection()
            self.legendDict['color'] = self.colorCtrl.GetStringSelection()
            dc = wx.PaintDC(self)
            dc.SetFont(wx.Font(   pointSize = self.legendDict['fontsize'], family = wx.FONTFAMILY_DEFAULT,
                                                style = wx.NORMAL, weight = wx.FONTWEIGHT_NORMAL))
            # position
            x = self.units.convert(value = float(self.xCoord.GetValue()), fromUnit = currUnit, toUnit = 'inch')
            y = self.units.convert(value = float(self.yCoord.GetValue()), fromUnit = currUnit, toUnit = 'inch')
            self.legendDict['where'] = (x, y)
            # estimated size
            if not self.defaultSize.GetValue():
                self.legendDict['defaultSize'] = False
            
                width = self.units.convert(value = float(self.widthCtrl.GetValue()), fromUnit = currUnit, toUnit = 'inch')
                height = self.units.convert(value = float(self.heightCtrl.GetValue()), fromUnit = currUnit, toUnit = 'inch')
            
                if rasterType in ('FCELL', 'DCELL'):
                    self.legendDict['width'] = width 
                    self.legendDict['height'] = height
                    textPart = self.units.convert(value = dc.GetTextExtent(maxim)[0], fromUnit = 'pixel', toUnit = 'inch')
                    drawWidth = width + textPart
                    drawHeight = height
                    self.legendDict['drawRect'] = Rect(x = x, y = y, width = drawWidth, height = drawHeight)
                else: #categorical map
                    self.legendDict['cols'] = self.colsCtrl.GetValue() 
                    cat = RunCommand(   'r.category', read = True, map = self.legendDict['raster'],
                                        fs = ':').strip().split('\n')
                    rows = ceil(float(len(cat))/self.legendDict['cols'])

                    drawHeight = self.units.convert(value =  1.5 *rows * self.legendDict['fontsize'], fromUnit = 'point', toUnit = 'inch')
                    self.legendDict['drawRect'] = Rect(x = x, y = y, width = width, height = drawHeight)

            else:
                self.legendDict['defaultSize'] = True
                if rasterType in ('FCELL', 'DCELL'):
                    textPart = self.units.convert(value = dc.GetTextExtent(maxim)[0], fromUnit = 'pixel', toUnit = 'inch')
                    drawWidth = self.units.convert( value = self.legendDict['fontsize'] * 2, 
                                                    fromUnit = 'point', toUnit = 'inch') + textpart
                                
                    drawHeight = self.units.convert(value = self.legendDict['fontsize'] * 10,
                                                    fromUnit = 'point', toUnit = 'inch')
                    self.legendDict['drawRect'] = Rect(x = x, y = y, width = drawWidth, height = drawHeight)
                    print self.legendDict['drawRect']
                else:#categorical map
                    self.legendDict['cols'] = self.colsCtrl.GetValue()
                    cat = RunCommand(   'r.category', read = True, map = self.legendDict['raster'],
                                        fs = ':').strip().split('\n')
                    rows = ceil(float(len(cat))/self.legendDict['cols'])
                    drawHeight = self.units.convert(value =  1.5 *rows * self.legendDict['fontsize'],
                                                    fromUnit = 'point', toUnit = 'inch')
                    paperWidth = self.parent.dialogDict['page']['Width']- self.parent.dialogDict['page']['Right']\
                                                                        - self.parent.dialogDict['page']['Left']
                    drawWidth = (paperWidth / self.legendDict['cols']) * (self.legendDict['cols'] - 1) + 1
                    self.legendDict['drawRect'] = Rect(x = x, y = y, width = drawWidth, height = drawHeight)
                    print self.legendDict['drawRect']
##                    labels = [each.split(':')[1] for each in cat]
##                    idx = labels.index(max(labels, key = len))
            
    
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
            'foo': wx.Pen(colour = "RED", width = 2),
            'map': wx.Pen(colour = "GREEN", width = 1),
            'box': wx.Pen(colour = 'RED', width = 2, style = wx.SHORT_DASH),
            'select': wx.Pen(colour = 'BLACK', width = 1, style = wx.SHORT_DASH)
            }
        self.brush = {
            'paper': wx.WHITE_BRUSH,
            'margins': wx.TRANSPARENT_BRUSH,            
            'foo': wx.GREEN_BRUSH,
            'map': wx.CYAN_BRUSH,
            'box': wx.TRANSPARENT_BRUSH,
            'select':wx.TRANSPARENT_BRUSH
            }    
        self.canvas = PsMapBufferedWindow(parent = self, mouse = self.mouse, pen = self.pen,
                                            brush = self.brush, cursors = self.cursors)
        self.canvas.SetCursor(self.cursors["default"])
        
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        
        self._layout()
        self.SetMinSize(wx.Size(700, 600))
        
        
    def DefaultData(self):
        """! Default settings"""
        self.defaultDict = {}
        self.defaultDict['page'] = dict(zip(PageSetupDialog(self, None).cat,
                                ['inch','a4','Portrait',8.268, 11.693, 0.5, 0.5, 1, 1]))
        self.defaultDict['map'] = dict(raster = None, rect = None, scaleType = 0, scale = None) 
        self.defaultDict['rasterLegend'] = dict(raster = None)
        
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
        if self.dialogDict['rasterLegend']:
            rLegendInstruction = "colortable y\n"
            rLegendInstruction += "    raster {raster}\n".format(**self.dialogDict['rasterLegend'])
            rLegendInstruction += "    where {rect.x} {rect.y}\n".format(**self.dialogDict['rasterLegend'])
            rLegendInstruction += "    width {rect.width}\n".format(**self.dialogDict['rasterLegend'])
            if self.dialogDict['rasterLegend']['type'] in ("FCELL", "DCELL"):
                rLegendInstruction += "    height {rect.height}\n".format(**self.dialogDict['rasterLegend'])
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
        dlg = PageSetupDialog(self, self.dialogDict['page']) 
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
            dlg = MapDialog(parent = self, mapDict = self.dialogDict['map'])
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
        # Add items to the menu
        AddLegend = wx.MenuItem(decmenu, wx.ID_ANY, Icons["addlegend"].GetLabel())
        AddLegend.SetBitmap(Icons["addlegend"].GetBitmap(self.iconsize))
        decmenu.AppendItem(AddLegend)
        self.Bind(wx.EVT_MENU, self.OnAddLegend, AddLegend)

        # Popup the menu.  If an item is selected then its handler
        # will be called before PopupMenu returns.
        self.PopupMenu(decmenu)
        decmenu.Destroy()
        
    def OnAddLegend(self, event):
        # basic info about rastr
        r={}
        dlg = LegendDialog(self, legendDict = self.dialogDict['rasterLegend'])
        dlg.ShowModal()
        dlg.Destroy()
        fontsize = 10
        if not self.dialogDict['map']['raster']:
            return
        type = RunCommand('r.info', flags = 't', read = True, map = self.dialogDict['map']['raster']).strip().split('=')[1]
        range = RunCommand('r.info', flags = 'r', read = True, map = self.dialogDict['map']['raster']).strip().split('\n')
        minim, maxim = range[0].split('=')[1], range[1].split('=')[1]
        if type in ('FCELL', 'DCELL'):
            bandWidth = 2 * fontsize + max(len(minim), len(maxim)) * fontsize/2
            bandHeight = 10 * fontsize
        if type == 'CELL':
            cat = RunCommand('r.category', read = True, map = self.dialogDict['map']['raster'], fs = ':').strip().split('\n')
            labelsLen = []
            for each in cat:
                labelsLen.append(len(each.split(':')[1]))
            bandHeight = len(cat) * fontsize + len(cat) * fontsize/2
            bandWidth = fontsize * 2 + max(labelsLen) * fontsize/2
            if max(labelsLen) == 0:
                bandHeight = 2 * fontsize + fontsize/2
                bandWidth = fontsize * 2 + 10 * fontsize/2
            
    def OnDelete(self, event):
        if self.canvas.dragId != -1:
            self.canvas.pdcObj.RemoveId(self.canvas.dragId)
            self.canvas.pdcTmp.RemoveAll()
            self.canvas.Refresh()
            self.SetDefault(type = self.canvas.itemType[self.canvas.dragId])
            del self.canvas.itemType[self.canvas.dragId]
            self.canvas.objectId.remove(self.canvas.dragId)
            
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
        self.DrawObj(self.pdcObj)
        
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

            
    def DrawObj(self, pdc):
        testRect = wx.Rect(0,0,100,100)
        rect = self.ScaleRect(testRect, self.currScale)
        rect.OffsetXY(200,300)
              
        id = wx.NewId()
        self.itemType[id] = 'foo'

        
        self.Draw(pen = self.pen[self.itemType[id]], brush = self.brush[self.itemType[id]], pdc = self.pdcObj,
                    pdctype = 'rect', drawid = id, bb = rect)
        self.objectId.append(id)

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
                self.parent.dialogDict['map']['rect'] = rectPaper 

                dlg = MapDialog(parent = self, mapDict = self.parent.dialogDict['map'])
                val = dlg.ShowModal()
                
                if val == wx.ID_OK:
                    self.parent.dialogDict['map'] = dlg.getInfo()
                    rectCanvas = self.CanvasPaperCoordinates(rect = self.parent.dialogDict['map']['rect'],
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
                    self.parent.dialogDict['map']['rect'] = None 
                    self.pdcTmp.RemoveId(self.idBoxTmp)
                    self.Refresh() 
                      
                dlg.Destroy()
                self.dragId = -1
            # recalculate the position of objects after dragging    
            if self.mouse['use'] == 'pointer' and self.dragId != -1:
                if self.itemType[self.dragId] == 'map':
                    self.parent.dialogDict['map']['rect'] = self.CanvasPaperCoordinates(rect = self.pdcObj.GetIdBounds(self.dragId),
                                                                canvasToPaper = True)
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
