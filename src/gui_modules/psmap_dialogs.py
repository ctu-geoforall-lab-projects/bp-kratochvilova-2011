
"""!
@package psmap_dialogs

@brief dialogs for ps.map

Classes:
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
from psmap import *
import wx
import wx.lib.scrolledpanel as scrolled

try:
    from agw import flatnotebook as fnb
except ImportError: # if it's not there locally, try the wxPython lib.
    import wx.lib.agw.flatnotebook as fnb


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
        self.OnIsLegend(None)
        self.OnRaster(None)
        self.OnDefaultSize(None)
        self.OnRange(None)
        self.OnDiscrete(None)
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
        self.isLegend.SetValue(self.legendDict['rLegend'])
        border.Add(item = self.isLegend, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)

        # choose raster
        
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Source raster")))
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        flexSizer = wx.FlexGridSizer (cols = 2, hgap = 5, vgap = 5)
        flexSizer.AddGrowableCol(1)
        
        self.rasterDefault = wx.RadioButton(panel, id = wx.ID_ANY, label = _("current raster"))
        self.rasterOther = wx.RadioButton(panel, id = wx.ID_ANY, label = _("select raster"))
        self.rasterDefault.SetValue(self.legendDict['rasterDefault'])#
        rasterType = RunCommand('r.info', flags = 't', read = True, map = self.parent.dialogDict['map']['raster']).strip().split('=')

        rasterType = rasterType[1] if rasterType[0] else 'None'
        self.rasterCurrent = wx.StaticText(panel, id = wx.ID_ANY, label = _("{0}: type {1}").format(self.parent.dialogDict['map']['raster'], rasterType))
        self.rasterSelect = Select( panel, id = wx.ID_ANY, size = globalvar.DIALOG_GSELECT_SIZE,
                                type = 'raster', multiple = False, mapsets = self.mapsets,
                                updateOnPopup = True, onPopup = None)
        self.rasterSelect.SetValue(self.legendDict['raster'] if not self.legendDict['rasterDefault'] else '')
        flexSizer.Add(self.rasterDefault, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        flexSizer.Add(self.rasterCurrent, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border = 10)
        flexSizer.Add(self.rasterOther, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        flexSizer.Add(self.rasterSelect, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border = 0)
        
        sizer.Add(item = flexSizer, proportion = 1, flag = wx.ALL | wx.EXPAND, border = 1)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        # size and position
        
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Size and position")))        
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        
        commentPosition = wx.StaticText(panel, id = wx.ID_ANY,\
                    label = _("Position of the top left corner\nfrom the top left edge of the paper"))
        units = wx.StaticText(panel, id = wx.ID_ANY, label = _("Units:"))
        choices = self.units.getPageUnits()
        self.unitsChoice = wx.Choice(panel, id = wx.ID_ANY, choices = choices)
        unitBox = wx.BoxSizer(wx.HORIZONTAL)
        unitBox.Add(units, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border = 10)
        unitBox.Add(self.unitsChoice, proportion = 1, flag = wx.ALL, border = 5)
        sizer.Add(unitBox, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        
        hBox = wx.BoxSizer(wx.HORIZONTAL)
        posBox = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Position"))) 
        posSizer = wx.StaticBoxSizer(posBox, wx.VERTICAL)       
        sizeBox = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Size"))) 
        sizeSizer = wx.StaticBoxSizer(sizeBox, wx.VERTICAL) 
        posGridBagSizer = wx.GridBagSizer(hgap = 10, vgap = 5)
        posGridBagSizer.AddGrowableRow(2)
        sizeGridBagSizer = wx.GridBagSizer(hgap = 5, vgap = 5)
        
        x = wx.StaticText(panel, id = wx.ID_ANY, label = _("X:"))
        y = wx.StaticText(panel, id = wx.ID_ANY, label = _("Y:"))
        self.xCoord = wx.TextCtrl(panel, id = wx.ID_ANY, value = str(self.legendDict['where'][0]))
        self.yCoord = wx.TextCtrl(panel, id = wx.ID_ANY, value = str(self.legendDict['where'][1]))
        self.defaultSize = wx.CheckBox(panel, id = wx.ID_ANY, label = _("Use default size"))
        self.defaultSize.SetValue(self.legendDict['defaultSize'])
        width = wx.StaticText(panel, id = wx.ID_ANY, label = _("Width:"))
        self.widthCtrl = wx.TextCtrl(panel, id = wx.ID_ANY, value = str(self.legendDict['width']))
        height = wx.StaticText(panel, id = wx.ID_ANY, label = _("Height:"))
        self.heightCtrl = wx.TextCtrl(panel, id = wx.ID_ANY, value = str(self.legendDict['height']))
        cols = wx.StaticText(panel, id = wx.ID_ANY, label = _("Columns:"))
        self.colsCtrl = wx.SpinCtrl(panel, id = wx.ID_ANY, value = "", min = 1, max = 10, initial = self.legendDict['cols'])
        self.colsCtrl.SetToolTipString(_("In case of discrete legend set number of columns instead of height"))
        self.heightCtrl.SetToolTipString(_("Only for floating point legend"))
        
        posGridBagSizer.Add(x, pos = (0,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        posGridBagSizer.Add(self.xCoord, pos = (0,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        posGridBagSizer.Add(y, pos = (1,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        posGridBagSizer.Add(self.yCoord, pos = (1,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        posGridBagSizer.Add(commentPosition, pos = (2,0), span = (1,2), flag =wx.ALIGN_BOTTOM, border = 0)
        posSizer.Add(posGridBagSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        
        sizeGridBagSizer.Add(self.defaultSize, pos = (0,0), span = (1,2), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        sizeGridBagSizer.Add(width, pos = (1,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        sizeGridBagSizer.Add(self.widthCtrl, pos = (1,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        sizeGridBagSizer.Add(height, pos = (2,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        sizeGridBagSizer.Add(self.heightCtrl, pos = (2,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        sizeGridBagSizer.Add(cols, pos = (3,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        sizeGridBagSizer.Add(self.colsCtrl, pos = (3,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        sizeSizer.Add(sizeGridBagSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        
        hBox.Add(posSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 3)
        hBox.Add(sizeSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 3)
        sizer.Add(hBox, proportion = 0, flag = wx.EXPAND, border = 0)
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
        self.fontCtrl.SetStringSelection(self.legendDict['font'])
        self.colorCtrl = wx.Choice(panel, id = wx.ID_ANY, choices = colorChoices)
        self.colorCtrl.SetStringSelection(self.legendDict['color'])
        self.fontSizeCtrl = wx.SpinCtrl(panel, id = wx.ID_ANY, min = 1, max = 99, initial = 10)
        self.fontSizeCtrl.SetValue(self.legendDict['fontsize'])
        
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
        self.ticks.SetValue(True if self.legendDict['tickbar'] == 'y' else False)
        # range
        if self.parent.dialogDict['map']['raster']:
            range = RunCommand('r.info', flags = 'r', read = True, map = self.parent.dialogDict['map']['raster']).strip().split('\n')
            self.minim, self.maxim = range[0].split('=')[1], range[1].split('=')[1]
        else:
            self.minim, self.maxim = 0,0
        self.range = wx.CheckBox(panel, id = wx.ID_ANY, label = _("range"))
        self.range.SetValue(self.legendDict['range'])
        minText =  wx.StaticText(panel, id = wx.ID_ANY, label = "{0} ({1})".format(_("min:"),self.minim))
        maxText =  wx.StaticText(panel, id = wx.ID_ANY, label = "{0} ({1})".format(_("max:"),self.maxim))
       
        self.min = wx.TextCtrl(panel, id = wx.ID_ANY, value = str(self.legendDict['min']))
        self.max = wx.TextCtrl(panel, id = wx.ID_ANY, value = str(self.legendDict['max']))
        self.discreteFcell = wx.CheckBox(panel, id = wx.ID_ANY, label = _("discrete range bands"))
        self.discreteFcell.SetValue(self.legendDict['discreteFcell'])
        
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
        self.nodata = wx.CheckBox(panel, id = wx.ID_ANY, label = _('draw "no data" box'))
        self.nodata.SetValue(True if self.legendDict['nodata'] == 'y' else False)
        #discrete
        self.discreteCell = wx.CheckBox(panel, id = wx.ID_ANY, label = _("discrete legend"))
        self.discreteCell.SetValue(self.legendDict['discreteCell'])
        
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
        self.Bind(wx.EVT_CHECKBOX, self.OnDiscrete, self.discreteCell)
        self.Bind(wx.EVT_CHECKBOX, self.OnDiscrete, self.discreteFcell)
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
    def OnDiscrete(self, event):
        if self.discreteCell.GetValue() or self.discreteFcell.GetValue():
            self.colsCtrl.Enable()
        else:
           self.colsCtrl.Disable()
        
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
            self.legendDict['rasterDefault'] = True
            self.legendDict['raster'] = self.parent.dialogDict['map']['raster']
        else:
            self.legendDict['rasterDefault'] = False
            self.legendDict['raster'] = self.rasterSelect.GetValue()
            
        if self.legendDict['raster']:
            # type and range of map
            rasterType = RunCommand('r.info', flags = 't', read = True, map = self.legendDict['raster']).strip().split('=')[1]
            self.legendDict['type'] = rasterType
            
            range = RunCommand('r.info', flags = 'r', read = True, map = self.legendDict['raster']).strip().split('\n')
            minim, maxim = range[0].split('=')[1], range[1].split('=')[1]
            
            #discrete
            if (self.legendDict['type'] == 'CELL' and self.discreteCell.GetValue()) or \
                self.legendDict['type'] != 'CELL' and self.discreteFcell.GetValue():
                self.legendDict['discrete'] = 'y'
            else:
                self.legendDict['discrete'] = 'n'   
            if self.discreteCell.GetValue():
                self.legendDict['discreteCell'] = True
            else:
                self.legendDict['discreteCell'] = False
            if self.discreteFcell.GetValue():
                self.legendDict['discreteFcell'] = True                
            else:
                self.legendDict['discreteFcell'] = False                 
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
            
                if self.legendDict['discrete'] == 'n':  #rasterType in ('FCELL', 'DCELL'):
                    self.legendDict['width'] = width 
                    self.legendDict['height'] = height
                    textPart = self.units.convert(value = dc.GetTextExtent(maxim)[0], fromUnit = 'pixel', toUnit = 'inch')
                    drawWidth = width + textPart
                    drawHeight = height
                    self.legendDict['rect'] = Rect(x = x, y = y, width = drawWidth, height = drawHeight)
                else: #categorical map
                    self.legendDict['cols'] = self.colsCtrl.GetValue() 
                    cat = RunCommand(   'r.category', read = True, map = self.legendDict['raster'],
                                        fs = ':').strip().split('\n')
                    rows = ceil(float(len(cat))/self.legendDict['cols'])

                    drawHeight = self.units.convert(value =  1.5 *rows * self.legendDict['fontsize'], fromUnit = 'point', toUnit = 'inch')
                    self.legendDict['rect'] = Rect(x = x, y = y, width = width, height = drawHeight)

            else:
                self.legendDict['defaultSize'] = True
                if self.legendDict['discrete'] == 'n':  #rasterType in ('FCELL', 'DCELL'):
                    textPart = self.units.convert(value = dc.GetTextExtent(maxim)[0], fromUnit = 'pixel', toUnit = 'inch')
                    drawWidth = self.units.convert( value = self.legendDict['fontsize'] * 2, 
                                                    fromUnit = 'point', toUnit = 'inch') + textPart
                                
                    drawHeight = self.units.convert(value = self.legendDict['fontsize'] * 10,
                                                    fromUnit = 'point', toUnit = 'inch')
                    self.legendDict['rect'] = Rect(x = x, y = y, width = drawWidth, height = drawHeight)
                else:#categorical map
                    self.legendDict['cols'] = self.colsCtrl.GetValue()
                    cat = RunCommand(   'r.category', read = True, map = self.legendDict['raster'],
                                        fs = ':').strip().split('\n')
                    if len(cat) == 1:# for discrete FCELL
                        rows = float(maxim)
                    else:
                        rows = ceil(float(len(cat))/self.legendDict['cols'])
                    drawHeight = self.units.convert(value =  1.5 *rows * self.legendDict['fontsize'],
                                                    fromUnit = 'point', toUnit = 'inch')
                    paperWidth = self.parent.dialogDict['page']['Width']- self.parent.dialogDict['page']['Right']\
                                                                        - self.parent.dialogDict['page']['Left']
                    drawWidth = (paperWidth / self.legendDict['cols']) * (self.legendDict['cols'] - 1) + 1
                    self.legendDict['rect'] = Rect(x = x, y = y, width = drawWidth, height = drawHeight)

##                    labels = [each.split(':')[1] for each in cat]
##                    idx = labels.index(max(labels, key = len))
                         
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
    def getInfo(self):
        return self.legendDict            