"""!
@package psmap_dialogs

@brief dialogs for ps.map

Classes:
 - UnitConversion
 - PageSetupDialog
 - MapDialog 
 - LegendDialog

(C) 2011 by Anna Kratochvilova, and the GRASS Development Team
This program is free software under the GNU General Public License
(>=v2). Read the file COPYING that comes with GRASS for details.

@author Anna Kratochvilova <anna.kratochvilova fsv.cvut.cz> (bachelor's project)
@author Martin Landa <landa.martin gmail.com> (mentor)
"""

import os
import sys
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
from   gselect    import Select
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
    
    
    
class PsmapDialog(wx.Dialog):
    def __init__(self, parent, title, settings = None):
        wx.Dialog.__init__(self, parent = parent, id = wx.ID_ANY, 
                            title = title, size = wx.DefaultSize, style = wx.DEFAULT_DIALOG_STYLE)
        self.dialogDict = settings
        self.unitConv = UnitConversion(self)

        
    def AddUnits(self, parent, dialogDict):
        self.units = dict()
        self.units['unitsLabel'] = wx.StaticText(parent, id = wx.ID_ANY, label = _("Units:"))
        choices = self.unitConv.getPageUnits()
        self.units['unitsCtrl'] = wx.Choice(parent, id = wx.ID_ANY, choices = choices)  
          
    def AddPosition(self, parent, dialogDict):
        self.position = dict()
        self.position['comment'] = wx.StaticText(parent, id = wx.ID_ANY,\
                    label = _("Position of the top left corner\nfrom the top left edge of the paper"))
        self.position['xLabel'] = wx.StaticText(parent, id = wx.ID_ANY, label = _("X:"))
        self.position['yLabel'] = wx.StaticText(parent, id = wx.ID_ANY, label = _("Y:"))
        self.position['xCtrl'] = wx.TextCtrl(parent, id = wx.ID_ANY, value = str(dialogDict['where'][0]))
        self.position['yCtrl'] = wx.TextCtrl(parent, id = wx.ID_ANY, value = str(dialogDict['where'][1]))
        
    def AddFont(self, parent, dialogDict):
        self.font = dict()
        self.font['fontLabel'] = wx.StaticText(parent, id = wx.ID_ANY, label = _("Choose font:"))
        self.font['colorLabel'] = wx.StaticText(parent, id = wx.ID_ANY, label = _("Choose color:"))
        self.font['fontCtrl'] = wx.FontPickerCtrl(parent, id = wx.ID_ANY)
        self.font['colorCtrl'] = wx.ColourPickerCtrl(parent, id = wx.ID_ANY, style=wx.FNTP_FONTDESC_AS_LABEL)
        self.font['fontCtrl'].SetSelectedFont(
                        wx.FontFromNativeInfoString(dialogDict['font'] + " " + str(dialogDict['fontsize'])))
        self.font['fontCtrl'].SetMaxPointSize(50)
        self.font['colorCtrl'].SetColour(dialogDict['color'])    
##        self.font['fontLabel'] = wx.StaticText(parent, id = wx.ID_ANY, label = _("Font:"))
##        self.font['fontSizeLabel'] = wx.StaticText(parent, id = wx.ID_ANY, label = _("Font size:"))
##        self.font['fontSizeUnitLabel'] = wx.StaticText(parent, id = wx.ID_ANY, label = _("points"))
##        self.font['colorLabel'] = wx.StaticText(parent, id = wx.ID_ANY, label = _("Color:"))
##        fontChoices = [ 'Times-Roman', 'Times-Italic', 'Times-Bold', 'Times-BoldItalic', 'Helvetica',\
##                        'Helvetica-Oblique', 'Helvetica-Bold', 'Helvetica-BoldOblique', 'Courier',\
##                        'Courier-Oblique', 'Courier-Bold', 'Courier-BoldOblique']
##        colorChoices = [  'aqua', 'black', 'blue', 'brown', 'cyan', 'gray', 'green', 'indigo', 'magenta',\
##                        'orange', 'purple', 'red', 'violet', 'white', 'yellow']
##        self.font['fontCtrl'] = wx.Choice(parent, id = wx.ID_ANY, choices = fontChoices)
##        self.font['fontCtrl'].SetStringSelection(dialogDict['font'])
##        self.colorCtrl = wx.Choice(parent, id = wx.ID_ANY, choices = colorChoices)
##        self.colorCtrl.SetStringSelection(self.legendDict['color'])
##        self.font['fontSizeCtrl']= wx.SpinCtrl(parent, id = wx.ID_ANY, min = 4, max = 50, initial = 10)
##        self.font['fontSizeCtrl'].SetValue(dialogDict['fontsize'])
##        self.font['colorCtrl'] = wx.ColourPickerCtrl(parent, id = wx.ID_ANY)
##        self.font['colorCtrl'].SetColour(dialogDict['color'])    
        
    def OnOK(self, event):
        event.Skip()
    def OnCancel(self, event):
        event.Skip()
    def _layout(self, panel):
        #buttons
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
        mainSizer.Add(item = panel, proportion = 1, flag = wx.EXPAND | wx.ALL, border = 5)
        mainSizer.Add(item = btnSizer, proportion = 0,
                      flag = wx.EXPAND | wx.ALL | wx.ALIGN_CENTER, border = 5)
        
        self.Bind(wx.EVT_CLOSE, self.OnCancel)
        
        self.SetSizer(mainSizer)
        mainSizer.Layout()
        mainSizer.Fit(self) 
            
class PageSetupDialog(PsmapDialog):
    def __init__(self, parent, settings = None):
        PsmapDialog.__init__(self, parent = parent, title = "Page setup")

        
        self.cat = ['Units', 'Format', 'Orientation', 'Width', 'Height', 'Left', 'Right', 'Top', 'Bottom']
        paperString = RunCommand('ps.map', flags = 'p', read = True)
        self.paperTable = self._toList(paperString) 
        self.unitsList = self.unitConv.getPageUnits()
        self.dialogDict = settings
        self.pageSetupDict = self.dialogDict['page']

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
            self.pageSetupDict[item] = self.unitConv.convert(value = float(self.getCtrl(item).GetValue()),
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
            newSize[item] = self.unitConv.convert(float(currPaper[item]), fromUnit = 'inch', toUnit = currUnit)

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
    
class MapDialog(PsmapDialog):
    def __init__(self, parent, settings = None):
        PsmapDialog.__init__(self, parent = parent, title = "Map settings")
        
        self.parent = parent
        self.dialogDict = settings
        self.mapDialogDict = self.dialogDict['map']
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
        currRegionDict = grass.region()

        rX = self.mapDialogDict['rect'].x
        rY = self.mapDialogDict['rect'].y
        rW = self.mapDialogDict['rect'].width
        rH = self.mapDialogDict['rect'].height
        
        mW = self.unitConv.convert(value = currRegionDict['e'] - currRegionDict['w'], fromUnit = 'meter', toUnit = 'inch')
        mH = self.unitConv.convert(value = currRegionDict['n'] - currRegionDict['s'], fromUnit = 'meter', toUnit = 'inch')
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
                             type = 'raster', multiple = False,
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
        #raster
        self.mapDialogDict['raster'] = self.select.GetValue() 
        #scale
        scaleType = self.choice.GetSelection()
        
        originRegionName = os.environ['WIND_OVERRIDE']
        if scaleType == 0: # automatic
            self.scale, self.rectAdjusted = self.AutoAdjust()
            self.mapDialogDict['rect'] = Rect(*self.rectAdjusted) 
            self.mapDialogDict['scaleType'] = 0
            self.mapDialogDict['scale'] = self.scale
            RunCommand('g.region', rast = self.mapDialogDict['raster'])
        elif scaleType == 1:
            self.mapDialogDict['scaleType'] = 1
            scaleNumber = float(self.textCtrl.GetValue().split(':')[1].strip())
            self.mapDialogDict['scale'] = 1/scaleNumber
            
            rectHalfInch = ( self.mapDialogDict['rect'].width/2, self.mapDialogDict['rect'].height/2)
            rectHalfMeter = ( self.unitConv.convert(value = rectHalfInch[0], fromUnit = 'inch', toUnit = 'meter')*scaleNumber,
                                self.unitConv.convert(value = rectHalfInch[1], fromUnit = 'inch', toUnit = 'meter')*scaleNumber) 
            currRegCentre = RunCommand('g.region', read = True, flags = 'cu', rast = self.mapDialogDict['raster'])
            currRegCentreDict = {}
            for item in currRegCentre.strip().split('\n'):
                currRegCentreDict[item.split(':')[0].strip()] = float(item.split(':')[1].strip())
            
            RunCommand('g.region', n = int(currRegCentreDict['center northing'] + rectHalfMeter[1]),
                       s = int(currRegCentreDict['center northing'] - rectHalfMeter[1]),
                       e = int(currRegCentreDict['center easting'] + rectHalfMeter[0]),
                       w = int(currRegCentreDict['center easting'] - rectHalfMeter[0]),
                       rast = self.mapDialogDict['raster'])
        
    def getInfo(self):
        return self.mapDialogDict
    
    def OnOK(self, event):
        self._update()
        event.Skip()
  


class LegendDialog(PsmapDialog):
    def __init__(self, parent, settings = None):
        PsmapDialog.__init__(self, parent = parent, title = "Legend settings")
        self.parent = parent
        self.dialogDict = settings
        self.legendDict = self.dialogDict['rasterLegend']
        self.units = UnitConversion(self)
        self.currRaster = self.dialogDict['map']['raster']
        
        #notebook
        notebook = wx.Notebook(parent = self, id = wx.ID_ANY, style = wx.BK_DEFAULT)
        self.panelRaster = self._rasterLegend(notebook)
        self.OnDefaultSize(None)
        self.OnRaster(None)
        self.OnRange(None)
        self.OnIsLegend(None)
        self._vectorLegend(notebook)  
        
        self._layout(notebook)
        
    def _rasterLegend(self, notebook):
        panel = scrolled.ScrolledPanel(parent = notebook, id = wx.ID_ANY, size = (-1, 500), style = wx.TAB_TRAVERSAL)
        panel.SetupScrolling(scroll_x = False, scroll_y = True)
        notebook.AddPage(page = panel, text = _("Raster legend"))

        border = wx.BoxSizer(wx.VERTICAL)
        # is legend
        self.isLegend = wx.CheckBox(panel, id = wx.ID_ANY, label = _("Add raster legend"))
        self.isLegend.SetValue(self.legendDict['rLegend'])
        border.Add(item = self.isLegend, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)

        # choose raster
        
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Source raster")))
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        flexSizer = wx.FlexGridSizer (cols = 2, hgap = 5, vgap = 5)
        flexSizer.AddGrowableCol(1)
        
        self.rasterDefault = wx.RadioButton(panel, id = wx.ID_ANY, label = _("current raster"), style = wx.RB_GROUP)
        self.rasterOther = wx.RadioButton(panel, id = wx.ID_ANY, label = _("select raster"))
        self.rasterDefault.SetValue(self.legendDict['rasterDefault'])#
        self.rasterOther.SetValue(not self.legendDict['rasterDefault'])#

        rasterType = self.getRasterType(map = self.currRaster)

        self.rasterCurrent = wx.StaticText(panel, id = wx.ID_ANY, label = _("{0}: type {1}").format(self.currRaster, str(rasterType)))
        self.rasterSelect = Select( panel, id = wx.ID_ANY, size = globalvar.DIALOG_GSELECT_SIZE,
                                    type = 'raster', multiple = False,
                                    updateOnPopup = True, onPopup = None)
        self.rasterSelect.SetValue(self.legendDict['raster'] if not self.legendDict['rasterDefault'] else '')
        flexSizer.Add(self.rasterDefault, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        flexSizer.Add(self.rasterCurrent, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border = 10)
        flexSizer.Add(self.rasterOther, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        flexSizer.Add(self.rasterSelect, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border = 0)
        
        sizer.Add(item = flexSizer, proportion = 1, flag = wx.ALL | wx.EXPAND, border = 1)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        # type of legend
        
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Type of legend")))        
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.discrete = wx.RadioButton(parent = panel, id = wx.ID_ANY, 
                        label = " {0} ".format(_("discrete legend (categorical maps)")), style = wx.RB_GROUP)
        self.continuous = wx.RadioButton(parent = panel, id = wx.ID_ANY, 
                        label = " {0} ".format(_("continuous color gradient legend (floating point map)")))
        
        vbox.Add(self.discrete, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 0)
        vbox.Add(self.continuous, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 0)
        sizer.Add(item = vbox, proportion = 1, flag = wx.ALL | wx.EXPAND, border = 1)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        # size and position
        
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Size and position")))        
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        #unit
        self.AddUnits(parent = panel, dialogDict = self.legendDict)
        unitBox = wx.BoxSizer(wx.HORIZONTAL)
        unitBox.Add(self.units['unitsLabel'], proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border = 10)
        unitBox.Add(self.units['unitsCtrl'], proportion = 1, flag = wx.ALL, border = 5)
        sizer.Add(unitBox, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        
        hBox = wx.BoxSizer(wx.HORIZONTAL)
        posBox = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Position"))) 
        posSizer = wx.StaticBoxSizer(posBox, wx.VERTICAL)       
        sizeBox = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Size"))) 
        sizeSizer = wx.StaticBoxSizer(sizeBox, wx.VERTICAL) 
        posGridBagSizer = wx.GridBagSizer(hgap = 10, vgap = 5)
        posGridBagSizer.AddGrowableRow(2)
        self.sizeGridBagSizer = wx.GridBagSizer(hgap = 5, vgap = 5)
        #position
        self.AddPosition(parent = panel, dialogDict = self.legendDict)
        #size
        self.defaultSize = wx.CheckBox(panel, id = wx.ID_ANY, label = _("Use default size"))
        self.defaultSize.SetValue(self.legendDict['defaultSize'])
        width = wx.StaticText(panel, id = wx.ID_ANY, label = _("Width:"))
        self.widthCtrl = wx.TextCtrl(panel, id = wx.ID_ANY, value = str(self.legendDict['width']))

        self.heightOrColumnsLabel = wx.StaticText(panel, id = wx.ID_ANY, label = _("Height:"))
        self.heightOrColumnsCtrl = wx.TextCtrl(panel, id = wx.ID_ANY, value = str(self.legendDict['height']))

        posGridBagSizer.Add(self.position['xLabel'], pos = (0,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        posGridBagSizer.Add(self.position['xCtrl'], pos = (0,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        posGridBagSizer.Add(self.position['yLabel'], pos = (1,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        posGridBagSizer.Add(self.position['yCtrl'], pos = (1,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        posGridBagSizer.Add(self.position['comment'], pos = (2,0), span = (1,2), flag =wx.ALIGN_BOTTOM, border = 0)
        posSizer.Add(posGridBagSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        
        self.sizeGridBagSizer.Add(self.defaultSize, pos = (0,0), span = (1,2), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        self.sizeGridBagSizer.Add(width, pos = (1,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        self.sizeGridBagSizer.Add(self.widthCtrl, pos = (1,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        self.sizeGridBagSizer.Add(self.heightOrColumnsLabel, pos = (2,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        self.sizeGridBagSizer.Add(self.heightOrColumnsCtrl, pos = (2,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        sizeSizer.Add(self.sizeGridBagSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        
        hBox.Add(posSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 3)
        hBox.Add(sizeSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 3)
        sizer.Add(hBox, proportion = 0, flag = wx.EXPAND, border = 0)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        # font settings
        
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Font settings")))
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        flexSizer = wx.FlexGridSizer (cols = 2, hgap = 5, vgap = 5)
        flexSizer.AddGrowableCol(1)
        
        self.AddFont(parent = panel, dialogDict = self.legendDict)
        
        flexSizer.Add(self.font['fontLabel'], proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        flexSizer.Add(self.font['fontCtrl'], proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        flexSizer.Add(self.font['colorLabel'], proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)        
        flexSizer.Add(self.font['colorCtrl'], proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        
        sizer.Add(item = flexSizer, proportion = 1, flag = wx.ALL | wx.EXPAND, border = 1)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        # advanced settings
        
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Advanced legend settings")))
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        gridBagSizer = wx.GridBagSizer (hgap = 5, vgap = 5)
        # no data
        self.nodata = wx.CheckBox(panel, id = wx.ID_ANY, label = _('draw "no data" box'))
        self.nodata.SetValue(True if self.legendDict['nodata'] == 'y' else False)
        #tickbar
        self.ticks = wx.CheckBox(panel, id = wx.ID_ANY, label = _("draw ticks across color table"))
        self.ticks.SetValue(True if self.legendDict['tickbar'] == 'y' else False)
        # range
        if self.dialogDict['map']['raster']:
            range = RunCommand('r.info', flags = 'r', read = True, map = self.dialogDict['map']['raster']).strip().split('\n')
            self.minim, self.maxim = range[0].split('=')[1], range[1].split('=')[1]
        else:
            self.minim, self.maxim = 0,0
        self.range = wx.CheckBox(panel, id = wx.ID_ANY, label = _("range"))
        self.range.SetValue(self.legendDict['range'])
        self.minText =  wx.StaticText(panel, id = wx.ID_ANY, label = "{0} ({1})".format(_("min:"),self.minim))
        self.maxText =  wx.StaticText(panel, id = wx.ID_ANY, label = "{0} ({1})".format(_("max:"),self.maxim))
       
        self.min = wx.TextCtrl(panel, id = wx.ID_ANY, value = str(self.legendDict['min']))
        self.max = wx.TextCtrl(panel, id = wx.ID_ANY, value = str(self.legendDict['max']))
        
        gridBagSizer.Add(self.nodata, pos = (0,0), span = (1,5), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.ticks, pos = (1,0), span = (1,5), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.range, pos = (2,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.minText, pos = (2,1), flag = wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border = 0)
        gridBagSizer.Add(self.min, pos = (2,2), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.maxText, pos = (2,3), flag = wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border = 0)
        gridBagSizer.Add(self.max, pos = (2,4), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        
        sizer.Add(gridBagSizer, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
   
        panel.SetSizer(border)
        panel.Fit()
        
        # bindings
        self.Bind(wx.EVT_RADIOBUTTON, self.OnRaster, self.rasterDefault)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnRaster, self.rasterOther)
        self.Bind(wx.EVT_CHECKBOX, self.OnIsLegend, self.isLegend)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnDiscrete, self.discrete)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnDiscrete, self.continuous)
        self.Bind(wx.EVT_CHECKBOX, self.OnDefaultSize, self.defaultSize)
        self.Bind(wx.EVT_CHECKBOX, self.OnRange, self.range)
        self.rasterSelect.GetTextCtrl().Bind(wx.EVT_TEXT, self.OnRaster)
        
        return panel
    
    def _vectorLegend(self, notebook):
        pass
        
        
    #   some enable/disable methods  
        
    def OnIsLegend(self, event):
        children = self.panelRaster.GetChildren()
        if self.isLegend.GetValue():
            for i,widget in enumerate(children):
                    widget.Enable()
            self.OnRaster(None)
            self.OnDefaultSize(None)
            self.OnRange(None)
            self.OnDiscrete(None)
        else:
            for i,widget in enumerate(children):
                if i != 0:
                    widget.Disable()
                    
    def OnRaster(self, event):
        if self.rasterDefault.GetValue():#default
            self.rasterSelect.Disable()
            type = self.getRasterType(self.currRaster)
        else:#select raster
            self.rasterSelect.Enable()
            map = self.rasterSelect.GetValue()
            type = self.getRasterType(map)
  
        if type == 'CELL':
            self.discrete.SetValue(True)
        elif type in ('FCELL', 'DCELL'):
            self.continuous.SetValue(True)
        if event is None:
            if self.legendDict['discrete'] == 'y':
                self.discrete.SetValue(True)
            elif self.legendDict['discrete'] == 'n':
                self.continuous.SetValue(True)
        self.OnDiscrete(None)
        
    def OnDiscrete(self, event):
        """! Change control according to the type of legend"""
        enabledSize = self.heightOrColumnsCtrl.IsEnabled()
        self.heightOrColumnsCtrl.Destroy()
        if self.discrete.GetValue():
            self.heightOrColumnsLabel.SetLabel("Columns:")
            self.heightOrColumnsCtrl = wx.SpinCtrl(self.panelRaster, id = wx.ID_ANY, value = "", min = 1, max = 10, initial = self.legendDict['cols'])
            self.heightOrColumnsCtrl.Enable(enabledSize)
            self.nodata.Enable()
            self.range.Disable()
            self.min.Disable()
            self.max.Disable()
            self.minText.Disable()
            self.maxText.Disable()
            self.ticks.Disable()
        else:
            self.heightOrColumnsLabel.SetLabel("Height:")
            self.heightOrColumnsCtrl = wx.TextCtrl(self.panelRaster, id = wx.ID_ANY, value = str(self.legendDict['height']))
            self.heightOrColumnsCtrl.Enable(enabledSize)
            self.nodata.Disable()
            self.range.Enable()
            if self.range.GetValue():
                self.minText.Enable()
                self.maxText.Enable()
                self.min.Enable()
                self.max.Enable()
            self.ticks.Enable()
        
        self.sizeGridBagSizer.Add(self.heightOrColumnsCtrl, pos = (2,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        self.panelRaster.Layout()
        self.panelRaster.Fit()
        
        
    def OnDefaultSize(self, event):
        if self.defaultSize.GetValue():
            self.widthCtrl.Disable()
            self.heightOrColumnsCtrl.Disable()        
        else:    
            self.widthCtrl.Enable()
            self.heightOrColumnsCtrl.Enable()
        
    def OnRange(self, event):
        if not self.range.GetValue():
            self.min.Disable()        
            self.max.Disable()
            self.minText.Disable()
            self.maxText.Disable()
        else:
            self.min.Enable()        
            self.max.Enable() 
            self.minText.Enable()
            self.maxText.Enable()           
        
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
        currUnit = self.units['unitsCtrl'].GetStringSelection()
        self.legendDict['unit'] = currUnit
        # raster
        if self.rasterDefault.GetValue():
            self.legendDict['rasterDefault'] = True
            self.legendDict['raster'] = self.currRaster
        else:
            self.legendDict['rasterDefault'] = False
            self.legendDict['raster'] = self.rasterSelect.GetValue()
            
        if self.legendDict['raster']:
            # type and range of map
            rasterType = self.getRasterType(self.legendDict['raster'])
            self.legendDict['type'] = rasterType
            
            range = RunCommand('r.info', flags = 'r', read = True, map = self.legendDict['raster']).strip().split('\n')
            minim, maxim = range[0].split('=')[1], range[1].split('=')[1]
            
            #discrete
            if self.discrete.GetValue():
                self.legendDict['discrete'] = 'y'
            else:
                self.legendDict['discrete'] = 'n'   
                    
            # font 
            font = self.font['fontCtrl'].GetSelectedFont()
            self.legendDict['font'] = font.GetFaceName()
            self.legendDict['fontsize'] = font.GetPointSize()
            self.legendDict['color'] = self.font['colorCtrl'].GetColour().GetAsString(flags = wx.C2S_NAME)
            dc = wx.PaintDC(self)
            dc.SetFont(wx.Font(   pointSize = self.legendDict['fontsize'], family = font.GetFamily(),
                                                style = font.GetStyle(), weight = wx.FONTWEIGHT_NORMAL))
            # position
            x = self.unitConv.convert(value = float(self.position['xCtrl'].GetValue()), fromUnit = currUnit, toUnit = 'inch')
            y = self.unitConv.convert(value = float(self.position['yCtrl'].GetValue()), fromUnit = currUnit, toUnit = 'inch')
            self.legendDict['where'] = (x, y)
            # estimated size
            if not self.defaultSize.GetValue():
                self.legendDict['defaultSize'] = False
            
                width = self.unitConv.convert(value = float(self.widthCtrl.GetValue()), fromUnit = currUnit, toUnit = 'inch')
                height = self.unitConv.convert(value = float(self.heightOrColumnsCtrl.GetValue()), fromUnit = currUnit, toUnit = 'inch')
            
                if self.legendDict['discrete'] == 'n':  #rasterType in ('FCELL', 'DCELL'):
                    self.legendDict['width'] = width 
                    self.legendDict['height'] = height
                    textPart = self.unitConv.convert(value = dc.GetTextExtent(maxim)[0], fromUnit = 'pixel', toUnit = 'inch')
                    drawWidth = width + textPart
                    drawHeight = height
                    self.legendDict['rect'] = Rect(x = x, y = y, width = drawWidth, height = drawHeight)
                else: #categorical map
                    self.legendDict['cols'] = self.heightOrColumnsCtrl.GetValue() 
                    cat = RunCommand(   'r.category', read = True, map = self.legendDict['raster'],
                                        fs = ':').strip().split('\n')
                    rows = ceil(float(len(cat))/self.legendDict['cols'])

                    drawHeight = self.unitConv.convert(value =  1.5 *rows * self.legendDict['fontsize'], fromUnit = 'point', toUnit = 'inch')
                    self.legendDict['rect'] = Rect(x = x, y = y, width = width, height = drawHeight)

            else:
                self.legendDict['defaultSize'] = True
                if self.legendDict['discrete'] == 'n':  #rasterType in ('FCELL', 'DCELL'):
                    textPart = self.unitConv.convert(value = dc.GetTextExtent(maxim)[0], fromUnit = 'pixel', toUnit = 'inch')
                    drawWidth = self.unitConv.convert( value = self.legendDict['fontsize'] * 2, 
                                                    fromUnit = 'point', toUnit = 'inch') + textPart
                                
                    drawHeight = self.unitConv.convert(value = self.legendDict['fontsize'] * 10,
                                                    fromUnit = 'point', toUnit = 'inch')
                    self.legendDict['rect'] = Rect(x = x, y = y, width = drawWidth, height = drawHeight)
                else:#categorical map
                    self.legendDict['cols'] = self.heightOrColumnsCtrl.GetValue()
                    cat = RunCommand(   'r.category', read = True, map = self.legendDict['raster'],
                                        fs = ':').strip().split('\n')
                    if len(cat) == 1:# for discrete FCELL
                        rows = float(maxim)
                    else:
                        rows = ceil(float(len(cat))/self.legendDict['cols'])
                    drawHeight = self.unitConv.convert(value =  1.5 *rows * self.legendDict['fontsize'],
                                                    fromUnit = 'point', toUnit = 'inch')
                    paperWidth = self.dialogDict['page']['Width']- self.dialogDict['page']['Right']\
                                                                        - self.dialogDict['page']['Left']
                    drawWidth = (paperWidth / self.legendDict['cols']) * (self.legendDict['cols'] - 1) + 1
                    self.legendDict['rect'] = Rect(x = x, y = y, width = drawWidth, height = drawHeight)


                         
            # no data
            if self.legendDict['discrete'] == 'y':
                if self.nodata.GetValue():
                    self.legendDict['nodata'] = 'y'
                else:
                    self.legendDict['nodata'] = 'n'
            # tickbar
            elif self.legendDict['discrete'] == 'n':
                if self.ticks.GetValue():
                    self.legendDict['tickbar'] = 'y'
                else:
                    self.legendDict['tickbar'] = 'n'
            # range
                if self.range.GetValue():
                    self.legendDict['range'] = True
                    self.legendDict['min'] = self.min.GetValue()
                    self.legendDict['max'] = self.max.GetValue()
                else:
                    self.legendDict['range'] = False
                        
    def getRasterType(self, map):
        rasterType = RunCommand('r.info', flags = 't', read = True, 
                                map = map).strip().split('=')
        return (rasterType[1] if rasterType[0] else None)
        
    
    def getInfo(self):
        return self.legendDict   
             
class MapinfoDialog(PsmapDialog):
    def __init__(self, parent, settings = None):
        PsmapDialog.__init__(self, parent = parent, title = "Mapinfo settings")
        self.parent = parent
        self.dialogDict = settings
        self.mapinfoDict = self.dialogDict['mapinfo'] 
        
        
        self.panel = self._mapinfoPanel()
     
        self._layout(self.panel)
        self.OnIsMapinfo(None)


    def _mapinfoPanel(self):
        panel = wx.Panel(parent = self, id = wx.ID_ANY, size = (-1, -1), style = wx.TAB_TRAVERSAL)
        #panel.SetupScrolling(scroll_x = False, scroll_y = True)
        border = wx.BoxSizer(wx.VERTICAL)
        
        
        # is info
        self.isMapinfo = wx.CheckBox(panel, id = wx.ID_ANY, label = _("Add mapinfo"))
        self.isMapinfo.SetValue(self.mapinfoDict['isInfo'])
        border.Add(item = self.isMapinfo, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        # position
        
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Position")))
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        gridBagSizer = wx.GridBagSizer (hgap = 5, vgap = 5)
        gridBagSizer.AddGrowableCol(1)
        
        self.AddPosition(parent = panel, dialogDict = self.mapinfoDict)
        self.AddUnits(parent = panel, dialogDict = self.mapinfoDict)
        gridBagSizer.Add(self.units['unitsLabel'], pos = (0,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.units['unitsCtrl'], pos = (0,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.position['xLabel'], pos = (1,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.position['xCtrl'], pos = (1,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.position['yLabel'], pos = (2,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.position['yCtrl'], pos = (2,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.position['comment'], pos = (3,0), span = (1,2), flag =wx.ALIGN_BOTTOM, border = 0)
        
        sizer.Add(gridBagSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        # font
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Font settings")))
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        gridBagSizer = wx.GridBagSizer (hgap = 5, vgap = 5)
        gridBagSizer.AddGrowableCol(1)
        
        self.AddFont(parent = panel, dialogDict = self.mapinfoDict)#creates font color too, used below
        
        gridBagSizer.Add(self.font['fontLabel'], pos = (0,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.font['fontCtrl'], pos = (0,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.font['colorLabel'], pos = (1,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)        
        gridBagSizer.Add(self.font['colorCtrl'], pos = (1,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)


        
        sizer.Add(item = gridBagSizer, proportion = 1, flag = wx.ALL | wx.EXPAND, border = 1)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        # colors
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Color settings")))
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        flexSizer = wx.FlexGridSizer (cols = 2, hgap = 5, vgap = 5)
        flexSizer.AddGrowableCol(1)
        
        self.colors = {}
        self.colors['borderCtrl'] = wx.CheckBox(panel, id = wx.ID_ANY, label = _("use border color:"))
        self.colors['backgroundCtrl'] = wx.CheckBox(panel, id = wx.ID_ANY, label = _("use background color:"))
        self.colors['borderColor'] = wx.ColourPickerCtrl(panel, id = wx.ID_ANY)
        self.colors['backgroundColor'] = wx.ColourPickerCtrl(panel, id = wx.ID_ANY)
        
        self.colors['borderCtrl'].SetValue(True if self.mapinfoDict['border'] != 'none' else False)
        self.colors['backgroundCtrl'].SetValue(True if self.mapinfoDict['background'] != 'none' else False)
        self.colors['borderColor'].SetColour(self.mapinfoDict['border'] 
                                            if self.mapinfoDict['border'] != 'none' else 'black')
        self.colors['backgroundColor'].SetColour(self.mapinfoDict['background'] 
                                            if self.mapinfoDict['background'] != 'none' else 'black')
        
        flexSizer.Add(self.colors['borderCtrl'], proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        flexSizer.Add(self.colors['borderColor'], proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        flexSizer.Add(self.colors['backgroundCtrl'], proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        flexSizer.Add(self.colors['backgroundColor'], proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        
        sizer.Add(item = flexSizer, proportion = 1, flag = wx.ALL | wx.EXPAND, border = 1)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        panel.SetSizer(border)
        
        self.Bind(wx.EVT_CHECKBOX, self.OnIsMapinfo, self.isMapinfo)
        self.Bind(wx.EVT_CHECKBOX, self.OnIsBorder, self.colors['borderCtrl'])
        self.Bind(wx.EVT_CHECKBOX, self.OnIsBackground, self.colors['backgroundCtrl'])
        
        return panel
    def OnIsBackground(self, event):
        if self.colors['backgroundCtrl'].GetValue():
            self.colors['backgroundColor'].Enable()
        else:
            self.colors['backgroundColor'].Disable()
                        
    def OnIsBorder(self, event):
        if self.colors['borderCtrl'].GetValue():
            self.colors['borderColor'].Enable()
        else:
            self.colors['borderColor'].Disable() 
                           
    def OnIsMapinfo(self, event):
        children = self.panel.GetChildren()
        if self.isMapinfo.GetValue():
            for i,widget in enumerate(children):
                    widget.Enable()
            self.OnIsBackground(None)
            self.OnIsBorder(None)
        else:
            for i,widget in enumerate(children):
                if i != 0:
                    widget.Disable()
                    
    def OnOK(self, event):
        self.update()
        event.Skip()
        
    def update(self):
        #is mapinfo
        if not self.isMapinfo.GetValue():
            self.mapinfoDict['isInfo'] = False
            return
        else:
            self.mapinfoDict['isInfo'] = True
        #units
        currUnit = self.units['unitsCtrl'].GetStringSelection()
        self.mapinfoDict['unit'] = currUnit
        # position
        x = self.unitConv.convert(value = float(self.position['xCtrl'].GetValue()), fromUnit = currUnit, toUnit = 'inch')
        y = self.unitConv.convert(value = float(self.position['yCtrl'].GetValue()), fromUnit = currUnit, toUnit = 'inch')
        self.mapinfoDict['where'] = (x, y)
        # font
        font = self.font['fontCtrl'].GetSelectedFont()
        self.mapinfoDict['font'] = font.GetFaceName()
        self.mapinfoDict['fontsize'] = font.GetPointSize()
        #colors
        self.mapinfoDict['color'] = self.font['colorCtrl'].GetColour().GetAsString(flags = wx.C2S_NAME)
        self.mapinfoDict['background'] = (self.colors['backgroundColor'].GetColour().GetAsString(flags = wx.C2S_NAME)
                                        if self.colors['backgroundCtrl'].GetValue() else 'none') 
        self.mapinfoDict['border'] = (self.colors['borderColor'].GetColour().GetAsString(flags = wx.C2S_NAME)
                                        if self.colors['borderCtrl'].GetValue() else 'none')
        
        # estimation of size
        w = self.mapinfoDict['fontsize'] * 15 
        h = self.mapinfoDict['fontsize'] * 5
        width = self.unitConv.convert(value = w, fromUnit = 'point', toUnit = 'inch')
        height = self.unitConv.convert(value = h, fromUnit = 'point', toUnit = 'inch')
        self.mapinfoDict['rect'] = Rect(x = x, y = y, width = width, height = height)
        
    def getInfo(self):
        return self.mapinfoDict 
        
        
##class TextDialog(PsmapDialog):
##    def __init__(self, parent, id, settings = None):
##        PsmapDialog.__init__(self, parent = parent, title = "Text settings")
##        self.parent = parent
##        self.dialogDict = settings
##        self.textDict = self.dialogDict['text'][id] 
##             
##        self.panel = self._textPanel()
##     
##        self._layout(self.panel)
##        self.OnIsText(None)
##        