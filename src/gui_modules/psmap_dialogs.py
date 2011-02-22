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
import string
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
import dbm_base
from   gselect    import Select
from   gcmd       import RunCommand

from grass.script import core as grass

import wx
import wx.lib.scrolledpanel as scrolled
import  wx.lib.filebrowsebutton as filebrowse
from wx.lib.expando import ExpandoTextCtrl, EVT_ETC_LAYOUT_NEEDED

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
    
    
class TCValidator(wx.PyValidator):
    """!validates input in textctrls, combobox, took from wx demo"""
    def __init__(self, flag = None):
        wx.PyValidator.__init__(self)
        self.flag = flag
        self.Bind(wx.EVT_CHAR, self.OnChar)

    def Clone(self):
        return TCValidator(self.flag)

    def Validate(self, win):
        print 'validate'
        tc = self.GetWindow()
        val = tc.GetValue()

        if self.flag == 'DIGIT_ONLY':
            for x in val:
                if x not in string.digits:
                    return False
        return True

    def OnChar(self, event):
        key = event.GetKeyCode()
        if key < wx.WXK_SPACE or key == wx.WXK_DELETE or key > 255:
            event.Skip()
            return
        if self.flag == 'DIGIT_ONLY' and chr(key) in string.digits:
            event.Skip()
            return
        if self.flag == 'SCALE' and chr(key) in string.digits + ':':
            event.Skip()
            return
        if self.flag == 'ZERO_AND_ONE_ONLY' and chr(key) in '01':
            event.Skip()
            return
        if not wx.Validator_IsSilent():
            wx.Bell()
        # Returning without calling even.Skip eats the event before it
        # gets to the text control
        return  

  
class PsmapDialog(wx.Dialog):
    def __init__(self, parent, title, settings, itemType):
        wx.Dialog.__init__(self, parent = parent, id = wx.ID_ANY, 
                            title = title, size = wx.DefaultSize, style = wx.DEFAULT_DIALOG_STYLE)
        self.dialogDict = settings
        self.itemType = itemType
        self.unitConv = UnitConversion(self)
        self.spinCtrlSize = (50, -1)

        
    def AddUnits(self, parent, dialogDict):
        self.units = dict()
        self.units['unitsLabel'] = wx.StaticText(parent, id = wx.ID_ANY, label = _("Units:"))
        choices = self.unitConv.getPageUnits()
        self.units['unitsCtrl'] = wx.Choice(parent, id = wx.ID_ANY, choices = choices)  
        self.units['unitsCtrl'].SetStringSelection(dialogDict['unit'])
          
    def AddPosition(self, parent, dialogDict):
        self.position = dict()
        self.position['comment'] = wx.StaticText(parent, id = wx.ID_ANY,\
                    label = _("Position of the top left corner\nfrom the top left edge of the paper"))
        self.position['xLabel'] = wx.StaticText(parent, id = wx.ID_ANY, label = _("X:"))
        self.position['yLabel'] = wx.StaticText(parent, id = wx.ID_ANY, label = _("Y:"))
        self.position['xCtrl'] = wx.TextCtrl(parent, id = wx.ID_ANY, value = str(dialogDict['where'][0]), validator = TCValidator(flag = 'DIGIT_ONLY'))
        self.position['yCtrl'] = wx.TextCtrl(parent, id = wx.ID_ANY, value = str(dialogDict['where'][1]), validator = TCValidator(flag = 'DIGIT_ONLY'))
        if dialogDict.has_key('unit'):
            x = self.unitConv.convert(value = dialogDict['where'][0], fromUnit = 'inch', toUnit = dialogDict['unit'])
            y = self.unitConv.convert(value = dialogDict['where'][1], fromUnit = 'inch', toUnit = dialogDict['unit'])
            self.position['xCtrl'].SetValue("{0:5.3f}".format(x))
            self.position['yCtrl'].SetValue("{0:5.3f}".format(y))
        
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
    def convertRGB(self, rgb):
        """!Converts wx.Colour(255,255,255,255) and string '255:255:255',
            depends on input"""    
        if type(rgb) == wx.Colour:
            return str(rgb.Red()) + ':' + str(rgb.Green()) + ':' + str(rgb.Blue())
        elif type(rgb) == str:
            return wx.Colour(*map(int, rgb.split(':')))
        
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
    def __init__(self, parent, settings, itemType):
        PsmapDialog.__init__(self, parent = parent, title = "Page setup",  settings = settings, itemType = itemType)

        
        self.cat = ['Units', 'Format', 'Orientation', 'Width', 'Height', 'Left', 'Right', 'Top', 'Bottom']
        paperString = RunCommand('ps.map', flags = 'p', read = True)
        self.paperTable = self._toList(paperString) 
        self.unitsList = self.unitConv.getPageUnits()
        pageId = find_key(dic = self.itemType, val = 'paper'), find_key(dic = self.itemType, val = 'margins')
        self.pageSetupDict = self.dialogDict[pageId]

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
    def __init__(self, parent, settings, itemType, region):
        PsmapDialog.__init__(self, parent = parent, title = "Raster map settings", settings = settings, itemType = itemType)
        
        mapId = find_key(dic = self.itemType, val = 'map')
        self.mapDialogDict = self.dialogDict[mapId]

        # original region without resolution
        self.currentRegionDict = region

        self.scale = [None]*3
        self.center = [None]*3
        
        #notebook
        notebook = wx.Notebook(parent = self, id = wx.ID_ANY, style = wx.BK_DEFAULT)
        self.panel = self._rasterPanel(notebook)
        
        self._layout(notebook)
        
        
        self.selectedRaster = self.mapDialogDict['raster']
        if self.mapDialogDict['raster']:
            self.select.SetValue(self.mapDialogDict['raster'])
        self.scaleChoice.SetSelection(self.mapDialogDict['scaleType'])
        
        self.OnRaster(None)
        self.scale[self.mapDialogDict['scaleType']] = self.mapDialogDict['scale']
        self.center[self.mapDialogDict['scaleType']] = self.mapDialogDict['center']
        self.OnScaleChoice(None)
        
    def _rasterPanel(self, notebook):
        panel = wx.Panel(parent = notebook, id = wx.ID_ANY, size = (-1, -1), style = wx.TAB_TRAVERSAL)
        notebook.AddPage(page = panel, text = _("Raster"))
        
        border = wx.BoxSizer(wx.VERTICAL)
        
        #pattern
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Raster")))        
        sizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)
        gridBagSizer = wx.GridBagSizer(hgap = 5, vgap = 5)
        gridBagSizer.AddGrowableCol(2,1)
        gridBagSizer.AddGrowableCol(4,1)

        rasterText = wx.StaticText(panel, id = wx.ID_ANY, label = _("Choose raster:"))
        self.select = Select(panel, id = wx.ID_ANY,# size = globalvar.DIALOG_GSELECT_SIZE,
                             type = 'raster', multiple = False,
                             updateOnPopup = True, onPopup = None)

        scaleText = wx.StaticText(panel, id = wx.ID_ANY, label = _("Scale: "))
        self.scaleChoice = wx.Choice(panel, id = wx.ID_ANY, choices = [_("Automatic - draw the entire raster"),
                                                                _("Automatic - draw current region"),
                                                                _("Fixed - the map centre given")])
        self.scaleTextCtrl = wx.TextCtrl(panel, id = wx.ID_ANY, value = "", style = wx.TE_RIGHT, validator = TCValidator('SCALE'))
        self.eastingText = wx.StaticText(panel, id = wx.ID_ANY, label = _("E: "))
        self.northingText = wx.StaticText(panel, id = wx.ID_ANY, label = _("N: "))
        self.eastingTextCtrl = wx.TextCtrl(panel, id = wx.ID_ANY, style = wx.TE_RIGHT, validator = TCValidator(flag = 'DIGIT_ONLY'))
        self.northingTextCtrl = wx.TextCtrl(panel, id = wx.ID_ANY, style = wx.TE_RIGHT, validator = TCValidator(flag = 'DIGIT_ONLY'))
        
        
            
        gridBagSizer.Add(rasterText, pos = (0, 0),  flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.select, pos = (0, 1), span = (1, 5),flag = wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border = 0)
        gridBagSizer.Add(scaleText, pos = (1, 0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.scaleChoice, pos = (1, 1), span = (1, 4), flag = wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border = 0)
        gridBagSizer.Add(self.scaleTextCtrl, pos = (1, 5), flag = wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border = 0)
        gridBagSizer.Add(self.eastingText, pos = (2, 1), flag = wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border = 0)
        gridBagSizer.Add(self.eastingTextCtrl, pos = (2, 2), flag = wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border = 0)
        gridBagSizer.Add(self.northingText, pos = (2, 3), flag = wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border = 0)
        gridBagSizer.Add(self.northingTextCtrl, pos = (2, 4), flag = wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border = 0)
        
        
        sizer.Add(gridBagSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        self.scaleChoice.Bind(wx.EVT_CHOICE, self.OnScaleChoice)
        self.select.GetTextCtrl().Bind(wx.EVT_TEXT, self.OnRaster)
        
        panel.SetSizer(border)
        panel.Fit()
        return panel  
      
##    def AutoAdjust(self, scaleType, raster = self.selectedRaster):
##        if scaleType == 0 and self.selectedRaster: # automatic, region from raster
##            res = grass.read_command("g.region", flags = 'gu', rast = self.selectedRaster)
##            currRegionDict = grass.parse_key_val(res, val_type = float)
##        elif scaleType == 1 and self.selectedRaster: # automatic, current region
##            currRegionDict = self.currentRegionDict
##        else:
##            return None, None
##
##        rX = self.mapDialogDict['rect'].x
##        rY = self.mapDialogDict['rect'].y
##        rW = self.mapDialogDict['rect'].width
##        rH = self.mapDialogDict['rect'].height
##        
##        mW = self.unitConv.convert(value = currRegionDict['e'] - currRegionDict['w'], fromUnit = 'meter', toUnit = 'inch')
##        mH = self.unitConv.convert(value = currRegionDict['n'] - currRegionDict['s'], fromUnit = 'meter', toUnit = 'inch')
##        scale = min(rW/mW, rH/mH)
##
##        if rW/rH > mW/mH:
##            x = rX - (rH*(mW/mH) - rW)/2
##            y = rY
##            rWNew = rH*(mW/mH)
##            rHNew = rH
##        else:
##            x = rX
##            y = rY - (rW*(mH/mW) - rH)/2
##            rHNew = rW*(mH/mW)
##            rWNew = rW
##        return scale, (x, y, rWNew, rHNew) #inch
    
    def RegionDict(self, scaleType):
        """!Returns region dictionary according to selected type of scale"""
        if scaleType == 0 and self.selectedRaster: # automatic, region from raster
            res = grass.read_command("g.region", flags = 'gu', rast = self.selectedRaster)
            return grass.parse_key_val(res, val_type = float)
        elif scaleType == 1 and self.selectedRaster: # automatic, current region
##            res = grass.read_command("g.region", flags = 'gu', region = self.currentRegionName)
            return self.currentRegionDict#grass.parse_key_val(res, val_type = float)
        return None

    def RegionCenter(self, regionDict):
        """!Returnes map center coordinates of given region dictionary"""
        
        if regionDict:
            cE = (regionDict['w'] + regionDict['e'])/2
            cN = (regionDict['n'] + regionDict['s'])/2
            return cE, cN
        return None
    
    def OnRaster(self, event):
        """!Selected raster changing"""
        
        self.selectedRaster = self.select.GetValue() if self.select.GetValue() else None
        self.scale[0], foo = AutoAdjust(self, scaleType = 0, raster = self.selectedRaster)
        self.scale[1], foo = AutoAdjust(self, scaleType = 1, raster = self.selectedRaster)
        self.scale[2] = None
        self.center[0] = self.RegionCenter(self.RegionDict(scaleType = 0))
        self.center[1] = self.RegionCenter(self.RegionDict(scaleType = 1))
        self.center[2] = None
        self.OnScaleChoice(None)
        
            
    def OnScaleChoice(self, event):
        """!Selected scale type changing"""
        
        scaleType = self.scaleChoice.GetSelection()
        if scaleType in (0, 1): # automatic - region from raster map, automatic - current region
            self.scaleTextCtrl.Disable()
            self.eastingTextCtrl.Disable()
            self.northingTextCtrl.Disable()
            if self.scale[scaleType]:
                self.scaleTextCtrl.SetValue("1 : {0:.0f}".format(1/self.scale[scaleType]))
            if self.center[scaleType]:
                self.eastingTextCtrl.SetValue(str(self.center[scaleType][0]))
                self.northingTextCtrl.SetValue(str(self.center[scaleType][1]))
        else: # fixed
            self.scaleTextCtrl.Enable()
            self.eastingTextCtrl.Enable()
            self.northingTextCtrl.Enable()
            if self.scale[scaleType]:
                self.scaleTextCtrl.SetValue("1 : {0:.0f}".format(1/self.scale[scaleType]))
            if self.center[scaleType]:
                self.eastingTextCtrl.SetValue(str(self.center[scaleType][0]))
                self.northingTextCtrl.SetValue(str(self.center[scaleType][1]))
            
           
            
    def _update(self):
        #raster
        self.mapDialogDict['raster'] = self.select.GetValue() 
        #scale
        scaleType = self.scaleChoice.GetSelection()
        
        if scaleType in (0, 1): # automatic - region from raster, current region
            if scaleType == 0:
                RunCommand('g.region', rast = self.mapDialogDict['raster'])
            else:
                RunCommand('g.region', rast = self.mapDialogDict['raster'], **self.currentRegionDict)

            self.scale, self.rectAdjusted = AutoAdjust(self, scaleType = scaleType, raster = self.selectedRaster)
            self.mapDialogDict['rect'] = self.rectAdjusted
            self.mapDialogDict['scaleType'] = scaleType
            self.mapDialogDict['scale'] = self.scale
            self.mapDialogDict['center'] = self.center[scaleType]
            
        elif scaleType == 2:
            self.mapDialogDict['scaleType'] = scaleType
            scaleNumber = float(self.scaleTextCtrl.GetValue().split(':')[1].strip())
            self.mapDialogDict['scale'] = 1/scaleNumber
            centerE = float(self.eastingTextCtrl.GetValue()) if not self.eastingTextCtrl.IsEmpty() else self.center[0][0]
            centerN = float(self.northingTextCtrl.GetValue()) if not self.northingTextCtrl.IsEmpty() else self.center[0][1]
            self.mapDialogDict['center'] = centerE, centerN
            
            ComputeSetRegion(self)
##            rectHalfInch = ( self.mapDialogDict['rect'].width/2, self.mapDialogDict['rect'].height/2)
##            rectHalfMeter = ( self.unitConv.convert(value = rectHalfInch[0], fromUnit = 'inch', toUnit = 'meter')*scaleNumber,
##                                self.unitConv.convert(value = rectHalfInch[1], fromUnit = 'inch', toUnit = 'meter')*scaleNumber) 
##
##           
##
##            RunCommand('g.region', n = int(centerN + rectHalfMeter[1]),
##                       s = int(centerN - rectHalfMeter[1]),
##                       e = int(centerE + rectHalfMeter[0]),
##                       w = int(centerE - rectHalfMeter[0]),
##                       rast = self.mapDialogDict['raster'])
        
    def getInfo(self):
        return self.mapDialogDict
    
    def OnOK(self, event):
        try:
            self._update()
            event.Skip()
        except IndexError:
            wx.MessageBox(message = _("Invalid scale!"),
                                    caption = _('Invalid scale'), style = wx.OK|wx.ICON_ERROR)
        
  
class MainVectorDialog(PsmapDialog):
    def __init__(self, parent, settings, itemType):
        PsmapDialog.__init__(self, parent = parent, title = "Choose vector maps", settings = settings, itemType = itemType)

        id = find_key(dic = self.itemType, val = 'vector')
        self.mainVectDict = self.dialogDict[id] 
        if self.mainVectDict['list']:
            self.vectorList = self.mainVectDict['list']
        else:
            self.vectorList = []
        self.mainVectDict['list'] = self.vectorList
        self.panel = self._vectorPanel()
     
        self._layout(self.panel)
        
    def _vectorPanel(self):
        panel = wx.Panel(parent = self, id = wx.ID_ANY, size = (-1, -1), style = wx.TAB_TRAVERSAL)
        border = wx.BoxSizer(wx.VERTICAL)
        
        # choose vector map
        
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Choose map")))
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        gridBagSizer = wx.GridBagSizer (hgap = 5, vgap = 5)
        
        text = wx.StaticText(panel, id = wx.ID_ANY, label = _("Map:"))
        self.select = Select(panel, id = wx.ID_ANY,# size = globalvar.DIALOG_GSELECT_SIZE,
                             type = 'vector', multiple = False,
                             updateOnPopup = True, onPopup = None)
        topologyType = [_("points"), _("lines"), _("areas")]
        self.vectorType = wx.RadioBox(panel, id = wx.ID_ANY, label = " {0} ".format(_("Data Type")), choices = topologyType,
                                        majorDimension = 3, style = wx.RA_SPECIFY_COLS)
        self.AddVector = wx.Button(panel, id = wx.ID_ANY, label = _("Add"))
        
        gridBagSizer.Add(text, pos = (0,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.select, pos = (0,1), span = (1, 2), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.vectorType, pos = (1,1), flag = wx.ALIGN_CENTER, border = 0)
        gridBagSizer.Add(self.AddVector, pos = (1,2), flag = wx.ALIGN_BOTTOM|wx.ALIGN_RIGHT, border = 0)
        
        sizer.Add(gridBagSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        # manage vector layers
        
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Vector maps order")))
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        gridBagSizer = wx.GridBagSizer (hgap = 5, vgap = 5)
        gridBagSizer.AddGrowableCol(0,2)
        gridBagSizer.AddGrowableCol(1,1)

        
        
        text = wx.StaticText(panel, id = wx.ID_ANY, label = _("The topmost vector map overlaps the others"))
        self.listbox = wx.ListBox(panel, id = wx.ID_ANY, choices = [], style = wx.LB_SINGLE|wx.LB_NEEDED_SB)
        self.btnUp = wx.Button(panel, id = wx.ID_ANY, label = _("Up"))
        self.btnDown = wx.Button(panel, id = wx.ID_ANY, label = _("Down"))
        self.btnDel = wx.Button(panel, id = wx.ID_ANY, label = _("Delete"))
        self.btnProp = wx.Button(panel, id = wx.ID_ANY, label = _("Properties"))
        
        self.updateListBox()
        
        
        gridBagSizer.Add(text, pos = (0,0), span = (1,2), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.listbox, pos = (1,0), span = (4, 1), flag = wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border = 0)
        gridBagSizer.Add(self.btnUp, pos = (1,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.btnDown, pos = (2,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.btnDel, pos = (3,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.btnProp, pos = (4,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        
        sizer.Add(gridBagSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        self.Bind(wx.EVT_BUTTON, self.OnAddVector, self.AddVector)
        self.Bind(wx.EVT_BUTTON, self.OnDelete, self.btnDel)
        self.Bind(wx.EVT_BUTTON, self.OnUp, self.btnUp)
        self.Bind(wx.EVT_BUTTON, self.OnDown, self.btnDown)
        self.Bind(wx.EVT_BUTTON, self.OnProperties, self.btnProp)
        
        panel.SetSizer(border)
        panel.Fit()
        return panel
    
    def OnAddVector(self, event):
        vmap = self.select.GetValue()
        if vmap:
            type = self.vectorType.GetStringSelection()
            record = "{0} - {1}".format(vmap,type)
            id = wx.NewId()
            self.vectorList.insert(0, [vmap, type, id])
            self.listbox.InsertItems([record], 0)
            self.itemType[id] = 'vProperties'
            self.dialogDict[id] = self.DefaultData(dataType = self.vectorList[0][1])
            
    def OnDelete(self, event):
        if self.listbox.GetSelections():
            pos = self.listbox.GetSelection()
            id = self.vectorList[pos][2]
            del self.vectorList[pos]
            del self.itemType[id]
            del self.dialogDict[id]
            self.updateListBox(selected = pos if pos < len(self.vectorList) -1 else len(self.vectorList) -1)
            
    def OnUp(self, event):
        if self.listbox.GetSelections():
            pos = self.listbox.GetSelection()
            if pos:
                self.vectorList.insert(pos - 1, self.vectorList.pop(pos))
            self.updateListBox(selected = (pos - 1) if pos > 0 else 0)
            
    def OnDown(self, event):
        if self.listbox.GetSelections():
            pos = self.listbox.GetSelection()
            if pos != len(self.vectorList) - 1:
                self.vectorList.insert(pos + 1, self.vectorList.pop(pos))
            self.updateListBox(selected = (pos + 1) if pos < len(self.vectorList) -1 else len(self.vectorList) -1)
    
    def OnProperties(self, event):
        if self.listbox.GetSelections():
            pos = self.listbox.GetSelection()
            id = self.vectorList[pos][2]

            dlg = VPropertiesDialog(self, settings = self.dialogDict, itemType = self.itemType, id = id)
            if dlg.ShowModal() == wx.ID_OK:
                self.dialogDict[id] = dlg.getInfo()

            dlg.Destroy()
           
    def DefaultData(self, dataType):
        if dataType == 'points':
            dd = dict(type = 'point or centroid', connection = False, layer = '1', masked = 'n', color = '0:0:0', width = 1,
                        fcolor = '255:0:0', rgbcolumn = None, symbol = os.path.join('basic', 'x'), eps = None,
                        size = 5, sizecolumn = None, scale = None,
                        rotation = False, rotate = 0, rotatecolumn = None)
        elif dataType == 'lines':
            dd = dict(type = 'line or boundary', connection = False, layer = '1', masked = 'n', color = '0:0:0', hwidth = 1,
                        hcolor = 'none', rgbcolumn = None,
                        width = 1, cwidth = None,
                        style = 'solid', linecap = 'butt')
        else:
            dd = dict(type = 'point or centroid', connection = False, layer = '1', masked = 'n', color = '0:0:0', width = 1,
                        fcolor = '255:0:0', rgbcolumn = None,
                        pat = None, pwidth = 1, scale = 1)
        return dd
    
    def updateListBox(self, selected = None):
        mapList = ["{0} - {1}".format(*item) for item in self.vectorList]
        self.listbox.Set(mapList)
        if selected is not None:
            self.listbox.SetSelection(selected)  
            self.listbox.EnsureVisible(selected)    
        
    def _update(self):
        self.mainVectDict['list'] = self.vectorList
        

    def getInfo(self):
        return self.mainVectDict
    
    def OnOK(self, event):
        self._update()
        event.Skip()
    
class VPropertiesDialog(PsmapDialog):
    def __init__(self, parent, settings, itemType, id):
        PsmapDialog.__init__(self, parent = parent, title = "", settings = settings, itemType = itemType)

        id = id
        self.vPropertiesDict = self.dialogDict[id]
        
        # determine map and its type
        vectorsId = find_key(dic = self.itemType, val = 'vector')
        for item in self.dialogDict[vectorsId]['list']:
            if id == item[2]:
                self.vectorName = item[0]
                self.type = item[1]
        self.SetTitle(self.vectorName + " "+ _("properties"))
        
        #vector map info
        self.mapDBInfo = dbm_base.VectorDBInfo(self.vectorName)
        self.layers = self.mapDBInfo.layers.keys()
        self.connection = True
        if len(self.layers) == 0:
            self.connection = False
        self.currLayer = self.vPropertiesDict['layer']
        
        #path to symbols, patterns
        gisbase = os.getenv("GISBASE")
        self.symbolPath = os.path.join(gisbase, 'etc', 'symbol')
        self.symbols = []
        for dir in os.listdir(self.symbolPath):
            for symbol in os.listdir(os.path.join(self.symbolPath, dir)):
                self.symbols.append(os.path.join(dir, symbol))
        self.patternPath = os.path.join(gisbase, 'etc', 'paint', 'patterns')

        #notebook
        notebook = wx.Notebook(parent = self, id = wx.ID_ANY, style = wx.BK_DEFAULT)
        self.DSpanel = self._DataSelectionPanel(notebook)
        self.EnableLayerSelection(enable = self.connection)
        selectPanel = { 'points': [self._ColorsPointAreaPanel, self._StylePointPanel], 
                        'lines': [self._ColorsLinePanel, self._StyleLinePanel], 
                        'areas': [self._ColorsPointAreaPanel, self._StyleAreaPanel]}
        self.ColorsPanel = selectPanel[self.type][0](notebook)
        
        self.OnOutline(None)
        if self.type in ('points', 'areas'):
            self.OnFill(None)
        self.OnColor(None)
        
        self.StylePanel = selectPanel[self.type][1](notebook)
        if self.type == 'points':
            self.OnSize(None)
            self.OnRotation(None)
        if self.type == 'areas':
            self.OnPattern(None)
        
        self._layout(notebook)
        
    def _DataSelectionPanel(self, notebook):
        panel = wx.Panel(parent = notebook, id = wx.ID_ANY, size = (-1, -1), style = wx.TAB_TRAVERSAL)
        notebook.AddPage(page = panel, text = _("Data selection"))
        
        border = wx.BoxSizer(wx.VERTICAL)
        
        # data type
        self.checkType1 = self.checkType2 = None
        if self.type in ('lines', 'points'):
            box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Feature type")))        
            sizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)
            gridBagSizer = wx.GridBagSizer(hgap = 5, vgap = 5)
            
            label = (_("points"), _("centroids")) if self.type == 'points' else (_("lines"), _("boundaries"))
            name = ("point", "centroid") if self.type == 'points' else ("line", "boundary")
            self.checkType1 = wx.CheckBox(panel, id = wx.ID_ANY, label = label[0], name = name[0])
            self.checkType2 = wx.CheckBox(panel, id = wx.ID_ANY, label = label[1], name = name[1])
            self.checkType1.SetValue(self.vPropertiesDict['type'].find(name[0]) >= 0)
            self.checkType2.SetValue(self.vPropertiesDict['type'].find(name[1]) >= 0)
            
            gridBagSizer.Add(self.checkType1, pos = (0,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
            gridBagSizer.Add(self.checkType2, pos = (0,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
            sizer.Add(gridBagSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
            border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        # layer selection
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Layer selection")))        
        sizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)
        self.gridBagSizerL = wx.GridBagSizer(hgap = 5, vgap = 5)
        
        
        self.warning =  wx.StaticText(panel, id = wx.ID_ANY, label = "")
        if not self.connection:
            self.warning = wx.StaticText(panel, id = wx.ID_ANY, label = _("Database connection is not defined in DB file."))
        text = wx.StaticText(panel, id = wx.ID_ANY, label = _("Select layer:"))
        self.layerChoice = wx.Choice(panel, id = wx.ID_ANY, choices = map(str, self.layers), size = self.spinCtrlSize)
        self.layerChoice.SetStringSelection(self.currLayer)
                
        table = self.mapDBInfo.layers[int(self.currLayer)]['table'] if self.connection else ""
        self.radioWhere = wx.RadioButton(panel, id = wx.ID_ANY, label = "SELECT * FROM {0} WHERE".format(table), style = wx.RB_GROUP)
        self.textCtrlWhere = wx.TextCtrl(panel, id = wx.ID_ANY, value = "")
        
        
        cols = self.mapDBInfo.GetColumns(self.mapDBInfo.layers[int(self.currLayer)]['table']) if self.connection else []
        self.choiceColumns = wx.Choice(panel, id = wx.ID_ANY, choices = cols)
        
        self.radioCats = wx.RadioButton(panel, id = wx.ID_ANY, label = "Choose categories ".format(table))
        self.textCtrlCats = wx.TextCtrl(panel, id = wx.ID_ANY, value = "")
        self.textCtrlCats.SetToolTipString(_("list of categories (e.g. 1,3,5-7)"))
        
        if self.vPropertiesDict.has_key('cats'):
            self.radioCats.SetValue(True)
            self.textCtrlCats.SetValue(self.vPropertiesDict['cats'])
        if self.vPropertiesDict.has_key('where'):
            self.radioWhere.SetValue(True)
            where = self.vPropertiesDict['where'].strip().split(" ",1)
            self.choiceColumns.SetStringSelection(where[0])
            self.textCtrlWhere.SetValue(where[1])
            
        row = 0
        if not self.connection:
            self.gridBagSizerL.Add(self.warning, pos = (0,0), span = (1,3), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
            row = 1
        self.gridBagSizerL.Add(text, pos = (0 + row,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        self.gridBagSizerL.Add(self.layerChoice, pos = (0 + row,1), flag = wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border = 0)
        self.gridBagSizerL.Add(self.radioWhere, pos = (1 + row,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        self.gridBagSizerL.Add(self.choiceColumns, pos = (1 + row,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)        
        self.gridBagSizerL.Add(self.textCtrlWhere, pos = (1 + row,2), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        self.gridBagSizerL.Add(self.radioCats, pos = (2 + row,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        self.gridBagSizerL.Add(self.textCtrlCats, pos = (2 + row,1), span = (1, 2), flag = wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border = 0)
        
        sizer.Add(self.gridBagSizerL, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        #mask
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Mask")))        
        sizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)
        
        self.mask = wx.CheckBox(panel, id = wx.ID_ANY, label = _("Use current mask"))
        self.mask.SetValue(True if self.vPropertiesDict['masked'] == 'y' else False)
        
        sizer.Add(self.mask, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)

        self.Bind(wx.EVT_CHOICE, self.OnLayer, self.layerChoice)
        
        panel.SetSizer(border)
        panel.Fit()
        return panel
    
    def _ColorsPointAreaPanel(self, notebook):
        panel = wx.Panel(parent = notebook, id = wx.ID_ANY, size = (-1, -1), style = wx.TAB_TRAVERSAL)
        notebook.AddPage(page = panel, text = _("Colors"))
        
        border = wx.BoxSizer(wx.VERTICAL)
        
        #colors - outline
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Outline")))        
        sizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)
        self.gridBagSizerO = wx.GridBagSizer(hgap = 5, vgap = 2)
        
        
        self.outlineCheck = wx.CheckBox(panel, id = wx.ID_ANY, label = _("draw outline"))
        self.outlineCheck.SetValue(self.vPropertiesDict['color'] != 'none')
        
        widthText = wx.StaticText(panel, id = wx.ID_ANY, label = _("Width (pts):"))
        self.widthSpin = wx.SpinCtrl(panel, id = wx.ID_ANY, min = 1, max = 25, initial = 1, size = self.spinCtrlSize)
        self.widthSpin.SetValue(self.vPropertiesDict['width'] if self.vPropertiesDict['color'] != 'none' else 1)
        
        colorText = wx.StaticText(panel, id = wx.ID_ANY, label = _("Color:"))
        self.colorPicker = wx.ColourPickerCtrl(panel, id = wx.ID_ANY)
        self.colorPicker.SetColour(self.convertRGB(self.vPropertiesDict['color']) if self.vPropertiesDict['color'] != 'none' else 'black')
        
        
        self.gridBagSizerO.Add(self.outlineCheck, pos = (0, 0), span = (1,2), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)        
        self.gridBagSizerO.Add(widthText, pos = (1, 1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)        
        self.gridBagSizerO.Add(self.widthSpin, pos = (1, 2), flag = wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border = 0)        
        self.gridBagSizerO.Add(colorText, pos = (2, 1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)                
        self.gridBagSizerO.Add(self.colorPicker, pos = (2, 2), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)        
        
        
        sizer.Add(self.gridBagSizerO, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        self.Bind(wx.EVT_CHECKBOX, self.OnOutline, self.outlineCheck)
        
        #colors - fill
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Fill")))        
        sizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)
        self.gridBagSizerF = wx.GridBagSizer(hgap = 5, vgap = 2)
       
        self.fillCheck = wx.CheckBox(panel, id = wx.ID_ANY, label = _("fill color"))
        self.fillCheck.SetValue(self.vPropertiesDict['fcolor'] != 'none' or self.vPropertiesDict['rgbcolumn'] is not None)
        

        self.colorPickerRadio = wx.RadioButton(panel, id = wx.ID_ANY, label = _("choose color:"), style = wx.RB_GROUP)
        #set choose color option if there is no db connection
        if self.connection:
            self.colorPickerRadio.SetValue(not self.vPropertiesDict['rgbcolumn'])
        else:
            self.colorPickerRadio.SetValue(False)            
        self.fillColorPicker = wx.ColourPickerCtrl(panel, id = wx.ID_ANY)
        self.fillColorPicker.SetColour(self.convertRGB(self.vPropertiesDict['fcolor']) if self.vPropertiesDict['fcolor'] != 'none' else 'red')
        
        
        self.colorColRadio = wx.RadioButton(panel, id = wx.ID_ANY, label = _("color from map table column:"))
        self.colorColChoice = self.getColsChoice(parent = panel)
        if self.connection:
            if self.vPropertiesDict['rgbcolumn']:
                self.colorColRadio.SetValue(True)
                self.colorColChoice.SetStringSelection(self.vPropertiesDict['rgbcolumn'])
            else:
                self.colorColRadio.SetValue(False)
                self.colorColChoice.SetSelection(0)
        self.colorColChoice.Enable(self.connection)
        self.colorColRadio.Enable(self.connection)
        
        self.gridBagSizerF.Add(self.fillCheck, pos = (0, 0), span = (1,2), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        self.gridBagSizerF.Add(self.colorPickerRadio, pos = (1, 1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)        
        self.gridBagSizerF.Add(self.fillColorPicker, pos = (1, 2), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)        
        self.gridBagSizerF.Add(self.colorColRadio, pos = (2, 1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)        
        self.gridBagSizerF.Add(self.colorColChoice, pos = (2, 2), flag = wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border = 0)        
        
        sizer.Add(self.gridBagSizerF, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)

        self.Bind(wx.EVT_CHECKBOX, self.OnFill, self.fillCheck)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnColor, self.colorColRadio)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnColor, self.colorPickerRadio)
        
        panel.SetSizer(border)
        panel.Fit()
        return panel
    
    def _ColorsLinePanel(self, notebook):
        panel = wx.Panel(parent = notebook, id = wx.ID_ANY, size = (-1, -1), style = wx.TAB_TRAVERSAL)
        notebook.AddPage(page = panel, text = _("Colors"))
        
        border = wx.BoxSizer(wx.VERTICAL)
        
        #colors - outline
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Outline")))        
        sizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)
        self.gridBagSizerO = wx.GridBagSizer(hgap = 5, vgap = 2)
        
        
        self.outlineCheck = wx.CheckBox(panel, id = wx.ID_ANY, label = _("draw outline"))
        self.outlineCheck.SetValue(self.vPropertiesDict['hcolor'] != 'none')
        self.outlineCheck.SetToolTipString(_("No effect for fill color from table column"))
        
        widthText = wx.StaticText(panel, id = wx.ID_ANY, label = _("Width (pts):"))
        self.widthSpin = wx.SpinCtrl(panel, id = wx.ID_ANY, min = 1, max = 25, initial = 1, size = self.spinCtrlSize)
        self.widthSpin.SetValue(self.vPropertiesDict['hwidth'] if self.vPropertiesDict['hcolor'] != 'none' else 1)
        
        colorText = wx.StaticText(panel, id = wx.ID_ANY, label = _("Color:"))
        self.colorPicker = wx.ColourPickerCtrl(panel, id = wx.ID_ANY)
        self.colorPicker.SetColour(self.convertRGB(self.vPropertiesDict['hcolor']) if self.vPropertiesDict['hcolor'] != 'none' else 'black')
        
        
        self.gridBagSizerO.Add(self.outlineCheck, pos = (0, 0), span = (1,2), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)        
        self.gridBagSizerO.Add(widthText, pos = (1, 1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)        
        self.gridBagSizerO.Add(self.widthSpin, pos = (1, 2), flag = wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border = 0)        
        self.gridBagSizerO.Add(colorText, pos = (2, 1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)                
        self.gridBagSizerO.Add(self.colorPicker, pos = (2, 2), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)        
        
        
        sizer.Add(self.gridBagSizerO, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        self.Bind(wx.EVT_CHECKBOX, self.OnOutline, self.outlineCheck)
        
        #colors - fill
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Fill")))        
        sizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)
        self.gridBagSizerF = wx.GridBagSizer(hgap = 5, vgap = 2)
       
        fillText = wx.StaticText(panel, id = wx.ID_ANY, label = _("Color of lines:"))
        

        self.colorPickerRadio = wx.RadioButton(panel, id = wx.ID_ANY, label = _("choose color:"), style = wx.RB_GROUP)
        #set choose color option if there is no db connection
        if self.connection:
            self.colorPickerRadio.SetValue(not self.vPropertiesDict['rgbcolumn'])
        else:
            self.colorPickerRadio.SetValue(False)            
        self.fillColorPicker = wx.ColourPickerCtrl(panel, id = wx.ID_ANY)
        self.fillColorPicker.SetColour(self.convertRGB(self.vPropertiesDict['color']) if self.vPropertiesDict['color'] != 'none' else 'black')
        
        
        self.colorColRadio = wx.RadioButton(panel, id = wx.ID_ANY, label = _("color from map table column:"))
        self.colorColChoice = self.getColsChoice(parent = panel)
        if self.connection:
            if self.vPropertiesDict['rgbcolumn']:
                self.colorColRadio.SetValue(True)
                self.colorColChoice.SetStringSelection(self.vPropertiesDict['rgbcolumn'])
            else:
                self.colorColRadio.SetValue(False)
                self.colorColChoice.SetSelection(0)
        self.colorColChoice.Enable(self.connection)
        self.colorColRadio.Enable(self.connection)
        
        self.gridBagSizerF.Add(fillText, pos = (0, 0), span = (1,2), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        self.gridBagSizerF.Add(self.colorPickerRadio, pos = (1, 1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)        
        self.gridBagSizerF.Add(self.fillColorPicker, pos = (1, 2), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)        
        self.gridBagSizerF.Add(self.colorColRadio, pos = (2, 1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)        
        self.gridBagSizerF.Add(self.colorColChoice, pos = (2, 2), flag = wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border = 0)        
        
        sizer.Add(self.gridBagSizerF, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)

        self.Bind(wx.EVT_RADIOBUTTON, self.OnColor, self.colorColRadio)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnColor, self.colorPickerRadio)
        panel.SetSizer(border)
        panel.Fit()
        return panel
    
    def _StylePointPanel(self, notebook):
        panel = wx.Panel(parent = notebook, id = wx.ID_ANY, size = (-1, -1), style = wx.TAB_TRAVERSAL)
        notebook.AddPage(page = panel, text = _("Size and style"))
        
        border = wx.BoxSizer(wx.VERTICAL)
        
        #symbology
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Symbology")))        
        sizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)
        gridBagSizer = wx.GridBagSizer(hgap = 5, vgap = 5)
        gridBagSizer.AddGrowableCol(1)
    
        self.symbolRadio = wx.RadioButton(panel, id = wx.ID_ANY, label = _("symbol:"), style = wx.RB_GROUP)
        self.symbolRadio.SetValue(bool(self.vPropertiesDict['symbol']))
            
         
        self.symbolChoice = wx.Choice(panel, id = wx.ID_ANY, choices = self.symbols)
            
        self.epsRadio = wx.RadioButton(panel, id = wx.ID_ANY, label = _("eps file:"))
        self.epsRadio.SetValue(bool(self.vPropertiesDict['eps']))
        
        self.epsFileCtrl = filebrowse.FileBrowseButton(panel, id = wx.ID_ANY, labelText = '',
                                buttonText =  _("Browse"), toolTip = _("Type filename or click browse to choose file"), 
                                dialogTitle = _("Choose a file"), startDirectory = '', initialValue = '',
                                fileMask = "Encapsulated PostScript (*.eps)|*.eps|All files (*.*)|*.*", fileMode = wx.OPEN)
        if self.vPropertiesDict['symbol']:
            self.symbolChoice.SetStringSelection(self.vPropertiesDict['symbol'])
            self.epsFileCtrl.SetValue('')
        else: #eps chosen
            self.epsFileCtrl.SetValue(self.vPropertiesDict['eps'])
            self.symbolChoice.SetSelection(0)
            
        gridBagSizer.Add(self.symbolRadio, pos = (0, 0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.symbolChoice, pos = (0, 1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.epsRadio, pos = (1, 0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.epsFileCtrl, pos = (1, 1), flag = wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border = 0)
        
        sizer.Add(gridBagSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        #size
        
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Size")))        
        sizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)
        gridBagSizer = wx.GridBagSizer(hgap = 5, vgap = 5)
        gridBagSizer.AddGrowableCol(0)
        
        self.sizeRadio = wx.RadioButton(panel, id = wx.ID_ANY, label = _("size:"), style = wx.RB_GROUP)
        self.sizeSpin = wx.SpinCtrl(panel, id = wx.ID_ANY, min = 1, max = 50, initial = 1)
        self.sizecolumnRadio = wx.RadioButton(panel, id = wx.ID_ANY, label = _("size from map table column:"))
        self.sizeColChoice = self.getColsChoice(panel)
        self.scaleText = wx.StaticText(panel, id = wx.ID_ANY, label = _("scale:"))
        self.scaleSpin = wx.SpinCtrl(panel, id = wx.ID_ANY, min = 1, max = 25, initial = 1)
        
        self.sizeRadio.SetValue(self.vPropertiesDict['size'] is not None)
        self.sizecolumnRadio.SetValue(bool(self.vPropertiesDict['sizecolumn']))
        self.sizeSpin.SetValue(self.vPropertiesDict['size'] if self.vPropertiesDict['size'] else 5)
        if self.vPropertiesDict['sizecolumn']:
            self.scaleSpin.SetValue(self.vPropertiesDict['scale'])
            self.sizeColChoice.SetStringSelection(self.vPropertiesDict['sizecolumn'])
        else:
            self.scaleSpin.SetValue(1)
            self.sizeColChoice.SetSelection(0)
        if not self.connection:   
            for each in (self.sizecolumnRadio, self.sizeColChoice, self.scaleSpin, self.scaleText):
                each.Disable()
            
        gridBagSizer.Add(self.sizeRadio, pos = (0, 0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.sizeSpin, pos = (0, 1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.sizecolumnRadio, pos = (1, 0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.sizeColChoice, pos = (1, 1), flag = wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border = 0)
        gridBagSizer.Add(self.scaleText, pos = (2, 0), flag = wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border = 0)
        gridBagSizer.Add(self.scaleSpin, pos = (2, 1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        
        sizer.Add(gridBagSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        self.Bind(wx.EVT_RADIOBUTTON, self.OnSize, self.sizeRadio)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnSize, self.sizecolumnRadio)
        
        #rotation
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Rotation")))        
        sizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)
        gridBagSizer = wx.GridBagSizer(hgap = 5, vgap = 5)
        gridBagSizer.AddGrowableCol(1)

        
        self.rotateCheck = wx.CheckBox(panel, id = wx.ID_ANY, label = _("rotate symbols:"))
        self.rotateRadio = wx.RadioButton(panel, id = wx.ID_ANY, label = _("counterclockwise in degrees:"), style = wx.RB_GROUP)
        self.rotateSpin = wx.SpinCtrl(panel, id = wx.ID_ANY, min = 0, max = 360, initial = 0)
        self.rotatecolumnRadio = wx.RadioButton(panel, id = wx.ID_ANY, label = _("from map table column:"))
        self.rotateColChoice = self.getColsChoice(panel)
        
        self.rotateCheck.SetValue(self.vPropertiesDict['rotation'])
        self.rotateRadio.SetValue(self.vPropertiesDict['rotate'] is not None)
        self.rotatecolumnRadio.SetValue(bool(self.vPropertiesDict['rotatecolumn']))
        self.rotateSpin.SetValue(self.vPropertiesDict['rotate'] if self.vPropertiesDict['rotate'] else 0)
        if self.vPropertiesDict['rotatecolumn']:
            self.rotateColChoice.SetStringSelection(self.vPropertiesDict['rotatecolumn'])
        else:
            self.rotateColChoice.SetSelection(0)
            
        gridBagSizer.Add(self.rotateCheck, pos = (0, 0), span = (1, 2), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.rotateRadio, pos = (1, 1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.rotateSpin, pos = (1, 2), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.rotatecolumnRadio, pos = (2, 1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.rotateColChoice, pos = (2, 2), flag = wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border = 0)
        
        sizer.Add(gridBagSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        self.Bind(wx.EVT_CHECKBOX, self.OnRotation, self.rotateCheck)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnRotationType, self.rotateRadio)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnRotationType, self.rotatecolumnRadio)
        
        panel.SetSizer(border)
        panel.Fit()
        return panel
    
    def _StyleLinePanel(self, notebook):
        panel = wx.Panel(parent = notebook, id = wx.ID_ANY, size = (-1, -1), style = wx.TAB_TRAVERSAL)
        notebook.AddPage(page = panel, text = _("Size and style"))
        
        border = wx.BoxSizer(wx.VERTICAL)
        
        #width
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Width")))        
        sizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)
        gridBagSizer = wx.GridBagSizer(hgap = 5, vgap = 5)
        
        widthText = wx.StaticText(panel, id = wx.ID_ANY, label = _("Set width:"))
        self.widthSpin = wx.SpinCtrl(panel, id = wx.ID_ANY, min = 1, max = 25, initial = 1)
        self.cwidthCheck = wx.CheckBox(panel, id = wx.ID_ANY, label = _("multiply width by category value"))
        
        if self.vPropertiesDict['width']:
            self.widthSpin.SetValue(self.vPropertiesDict['width'])
            self.cwidthCheck.SetValue(False)
        else:
            self.widthSpin.SetValue(self.vPropertiesDict['cwidth'])
            self.cwidthCheck.SetValue(True)
        
        gridBagSizer.Add(widthText, pos = (0, 0),  flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.widthSpin, pos = (0, 1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.cwidthCheck, pos = (1, 0), span = (1, 2), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        
        sizer.Add(gridBagSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        #style
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Line style")))        
        sizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)
        gridBagSizer = wx.GridBagSizer(hgap = 5, vgap = 5)
        
        styleText = wx.StaticText(panel, id = wx.ID_ANY, label = _("Choose line style:"))
        self.styleCombo = wx.ComboBox(panel, id = wx.ID_ANY,
                            choices = ["solid", "dashed", "dotted", "dashdotted"],
                            validator = TCValidator(flag = 'ZERO_AND_ONE_ONLY'))
        self.styleCombo.SetToolTipString(_("It's possible to enter a series of 0's and 1's too. "\
                                    "The first block of repeated zeros or ones represents 'draw', "\
                                    "the second block represents 'blank'. An even number of blocks "\
                                    "will repeat the pattern, an odd number of blocks will alternate the pattern."))
        linecapText = wx.StaticText(panel, id = wx.ID_ANY, label = _("Choose linecap:"))
        self.linecapChoice = wx.Choice(panel, id = wx.ID_ANY, choices = ["butt", "round", "extended_butt"])
        
        self.styleCombo.SetValue(self.vPropertiesDict['style'])
        self.linecapChoice.SetStringSelection(self.vPropertiesDict['linecap'])
        
        gridBagSizer.Add(styleText, pos = (0, 0),  flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.styleCombo, pos = (0, 1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(linecapText, pos = (1, 0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.linecapChoice, pos = (1, 1), flag = wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border = 0)
        
        sizer.Add(gridBagSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        panel.SetSizer(border)
        panel.Fit()
        return panel
        
    def _StyleAreaPanel(self, notebook):
        panel = wx.Panel(parent = notebook, id = wx.ID_ANY, size = (-1, -1), style = wx.TAB_TRAVERSAL)
        notebook.AddPage(page = panel, text = _("Size and style"))
        
        border = wx.BoxSizer(wx.VERTICAL)
        
        #pattern
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Pattern")))        
        sizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)
        gridBagSizer = wx.GridBagSizer(hgap = 5, vgap = 5)
        gridBagSizer.AddGrowableCol(1)
        
        self.patternCheck = wx.CheckBox(panel, id = wx.ID_ANY, label = _("use pattern:"))
        self.patFileCtrl = filebrowse.FileBrowseButton(panel, id = wx.ID_ANY, labelText = _("Choose pattern file:"),
                                buttonText =  _("Browse"), toolTip = _("Type filename or click browse to choose file"), 
                                dialogTitle = _("Choose a file"), startDirectory = self.patternPath, initialValue = '',
                                fileMask = "Encapsulated PostScript (*.eps)|*.eps|All files (*.*)|*.*", fileMode = wx.OPEN)
        self.patWidthText = wx.StaticText(panel, id = wx.ID_ANY, label = _("pattern line width:"))
        self.patWidthSpin = wx.SpinCtrl(panel, id = wx.ID_ANY, min = 1, max = 25, initial = 1)
        self.patScaleText = wx.StaticText(panel, id = wx.ID_ANY, label = _("pattern scale factor:"))
        self.patScaleSpin = wx.SpinCtrl(panel, id = wx.ID_ANY, min = 1, max = 25, initial = 1)
        
        self.patternCheck.SetValue(bool(self.vPropertiesDict['pat']))
        if self.patternCheck.GetValue():
            self.patFileCtrl.SetValue(self.vPropertiesDict['pat'])
            self.patWidthSpin.SetValue(self.vPropertiesDict['pwidth'])
            self.patScaleSpin.SetValue(self.vPropertiesDict['scale'])
        
        gridBagSizer.Add(self.patternCheck, pos = (0, 0),  flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.patFileCtrl, pos = (1, 0), span = (1, 2),flag = wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border = 0)
        gridBagSizer.Add(self.patWidthText, pos = (2, 0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.patWidthSpin, pos = (2, 1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.patScaleText, pos = (3, 0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.patScaleSpin, pos = (3, 1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        
        
        sizer.Add(gridBagSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        self.Bind(wx.EVT_CHECKBOX, self.OnPattern, self.patternCheck)
        
        panel.SetSizer(border)
        panel.Fit()
        return panel
        

    def OnLayer(self, event):
        """!Change columns on layer change """
        if self.layerChoice.GetStringSelection() == self.currLayer:
            return
        self.currLayer = self.layerChoice.GetStringSelection()
        cols = self.mapDBInfo.GetColumns(self.mapDBInfo.layers[int(self.currLayer)]['table']) if self.connection else []
        self.choiceColumns.SetItems(cols)

        self.choiceColumns.SetSelection(0)
        if self.type in ('points', 'lines'):
            self.colorColChoice.SetItems(cols)
            self.colorColChoice.SetSelection(0)
            
    def OnOutline(self, event):
        for widget in self.gridBagSizerO.GetChildren():
            if widget.GetWindow() != self.outlineCheck:
                widget.GetWindow().Enable(self.outlineCheck.GetValue())
                
    def OnFill(self, event):
        enable = self.fillCheck.GetValue()
        
        self.colorColChoice.Enable(enable)
        self.colorColRadio.Enable(enable)
        self.fillColorPicker.Enable(enable)
        self.colorPickerRadio.Enable(enable)
        if enable:
            self.OnColor(None)
        if not self.connection:
            self.colorColChoice.Disable()
            self.colorColRadio.Disable()
            
    def OnColor(self, event):
        self.colorColChoice.Enable(self.colorColRadio.GetValue())
        self.fillColorPicker.Enable(self.colorPickerRadio.GetValue())
            
    def OnSize(self, event):
        self.sizeSpin.Enable(self.sizeRadio.GetValue())
        self.sizeColChoice.Enable(self.sizecolumnRadio.GetValue())
        self.scaleText.Enable(self.sizecolumnRadio.GetValue())
        self.scaleSpin.Enable(self.sizecolumnRadio.GetValue())
        
    def OnRotation(self, event):
        for each in (self.rotateRadio, self.rotatecolumnRadio, self.rotateColChoice, self.rotateSpin):
            if self.rotateCheck.GetValue():
                each.Enable()
                self.OnRotationType(event = None)     
            else:
                each.Disable()
           
        
    def OnRotationType(self, event):
        self.rotateSpin.Enable(self.rotateRadio.GetValue())
        self.rotateColChoice.Enable(self.rotatecolumnRadio.GetValue())
        
    def OnPattern(self, event):
        for each in (self.patFileCtrl, self.patWidthText, self.patWidthSpin, self.patScaleText, self.patScaleSpin):
            each.Enable(self.patternCheck.GetValue())
            
    def EnableLayerSelection(self, enable = True):
        for widget in self.gridBagSizerL.GetChildren():
            if widget.GetWindow() != self.warning:
                widget.GetWindow().Enable(enable)
                
    def getColsChoice(self, parent):
        """!Returns a wx.Choice with table columns"""
        cols = self.mapDBInfo.GetColumns(self.mapDBInfo.layers[int(self.currLayer)]['table']) if self.connection else []
        choice = wx.Choice(parent = parent, id = wx.ID_ANY, choices = cols)
        return choice
        
    def _update(self):
        #feature type
        if self.type in ('lines', 'points'):
            featureType = None
            if self.checkType1.GetValue():
                featureType = self.checkType1.GetName()
                if self.checkType2.GetValue():
                    featureType += " or " + self.checkType2.GetName()
            elif self.checkType2.GetValue():
                featureType = self.checkType2.GetName()
            if featureType:
                self.vPropertiesDict['type'] = featureType
            
        # is connection
        self.vPropertiesDict['connection'] = self.connection
        if self.connection:
            self.vPropertiesDict['layer'] = self.layerChoice.GetStringSelection()
            if self.radioCats.GetValue() and not self.textCtrlCats.IsEmpty():
                self.vPropertiesDict['cats'] = self.textCtrlCats.GetValue()
            elif self.radioWhere.GetValue() and not self.textCtrlWhere.IsEmpty():
                self.vPropertiesDict['where'] = self.choiceColumns.GetStringSelection() + " " \
                                                                + self.textCtrlWhere.GetValue()
        #mask
        self.vPropertiesDict['masked'] = 'y' if self.mask.GetValue() else 'n'
        
        #colors
        if self.type in ('points', 'areas'):
            if self.outlineCheck.GetValue():
                self.vPropertiesDict['color'] = self.convertRGB(self.colorPicker.GetColour())
                self.vPropertiesDict['width'] = self.widthSpin.GetValue()
            else:
                self.vPropertiesDict['color'] = 'none'
                
            if self.fillCheck.GetValue():
                if self.colorPickerRadio.GetValue():
                    self.vPropertiesDict['fcolor'] = self.convertRGB(self.fillColorPicker.GetColour())
                    self.vPropertiesDict['rgbcolumn'] = None
                if self.colorColRadio.GetValue():
                    self.vPropertiesDict['fcolor'] = 'none'# this color is taken in case of no record in rgb column
                    self.vPropertiesDict['rgbcolumn'] = self.colorColChoice.GetStringSelection()
            else:
                self.vPropertiesDict['fcolor'] = 'none'    
                
        if self.type == 'lines':
                #hcolor only when no rgbcolumn
            if self.outlineCheck.GetValue():# and self.fillCheck.GetValue() and self.colorColRadio.GetValue():
                self.vPropertiesDict['hcolor'] = self.convertRGB(self.colorPicker.GetColour())
                self.vPropertiesDict['hwidth'] = self.widthSpin.GetValue()
            else:
                self.vPropertiesDict['hcolor'] = 'none'
                
            if self.colorPickerRadio.GetValue():
                self.vPropertiesDict['color'] = self.convertRGB(self.fillColorPicker.GetColour())
                self.vPropertiesDict['rgbcolumn'] = None
            if self.colorColRadio.GetValue():
                self.vPropertiesDict['color'] = 'none'# this color is taken in case of no record in rgb column
                self.vPropertiesDict['rgbcolumn'] = self.colorColChoice.GetStringSelection()
        #
        #size and style
        #
        
        if self.type == 'points':
            #symbols
            if self.symbolRadio.GetValue():
                self.vPropertiesDict['symbol'] = self.symbolChoice.GetStringSelection()
                self.vPropertiesDict['eps'] = None
            else:
                self.vPropertiesDict['eps'] = self.epsFileCtrl.GetValue()
                self.vPropertiesDict['symbol'] = None
            #size
            if self.sizeRadio.GetValue():
                self.vPropertiesDict['size'] = self.sizeSpin.GetValue()
                self.vPropertiesDict['sizecolumn'] = None
                self.vPropertiesDict['scale'] = None
            else:
                self.vPropertiesDict['sizecolumn'] = self.sizeColChoice.GetStringSelection()
                self.vPropertiesDict['scale'] = self.scaleSpin.GetValue()
                self.vPropertiesDict['size'] = None
            
            #rotation
            self.vPropertiesDict['rotate'] = None
            self.vPropertiesDict['rotatecolumn'] = None
            self.vPropertiesDict['rotation'] = False
            if self.rotateCheck.GetValue():
                self.vPropertiesDict['rotation'] = True
            if self.rotateRadio.GetValue():
                self.vPropertiesDict['rotate'] = self.rotateSpin.GetValue()
            else:
                self.vPropertiesDict['rotatecolumn'] = self.rotateColChoice.GetStringSelection()
                
        if self.type == 'areas':
            #pattern
            self.vPropertiesDict['pat'] = None 
            if self.patternCheck.GetValue() and bool(self.patFileCtrl.GetValue()):
                self.vPropertiesDict['pat'] = self.patFileCtrl.GetValue()
                self.vPropertiesDict['pwidth'] = self.patWidthSpin.GetValue()
                self.vPropertiesDict['scale'] = self.patScaleSpin.GetValue()
                
        if self.type == 'lines':
            #width
            if self.cwidthCheck.GetValue():
                self.vPropertiesDict['cwidth'] = self.widthSpin.GetValue()
                self.vPropertiesDict['width'] = None
            else:
                self.vPropertiesDict['width'] = self.widthSpin.GetValue()
                self.vPropertiesDict['cwidth'] = None
            #line style
            self.vPropertiesDict['style'] = self.styleCombo.GetValue() if self.styleCombo.GetValue() else 'solid'
            self.vPropertiesDict['linecap'] = self.linecapChoice.GetStringSelection()
            
    def getInfo(self):
        return self.vPropertiesDict
    
    def OnOK(self, event):
        self._update()
        event.Skip()
        
class LegendDialog(PsmapDialog):
    def __init__(self, parent, settings, itemType):
        PsmapDialog.__init__(self, parent = parent, title = "Legend settings", settings = settings, itemType = itemType)
        
        self.mapId = find_key(dic = self.itemType, val = 'map')

        self.pageId = find_key(dic = self.itemType, val = 'paper'), find_key(dic = self.itemType, val = 'margins')
        rLegendId = find_key(dic = self.itemType, val = 'rasterLegend')
        
        self.legendDict = self.dialogDict[rLegendId]
        self.currRaster = self.dialogDict[self.mapId]['raster'] if self.mapId else None
        
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
        self.isLegend = wx.CheckBox(panel, id = wx.ID_ANY, label = _("Show raster legend"))
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
        if self.mapId and self.dialogDict[self.mapId]['raster']:
            range = RunCommand('r.info', flags = 'r', read = True, map = self.dialogDict[self.mapId]['raster']).strip().split('\n')
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
            self.heightOrColumnsLabel.SetLabel(_("Columns:"))
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
            self.heightOrColumnsLabel.SetLabel(_("Height:"))
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
                    paperWidth = self.dialogDict[self.pageId]['Width']- self.dialogDict[self.pageId]['Right']\
                                                                        - self.dialogDict[self.pageId]['Left']
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
    def __init__(self, parent, settings, itemType):
        PsmapDialog.__init__(self, parent = parent, title = "Mapinfo settings", settings = settings, itemType = itemType)
        mapInfoId = find_key(dic = self.itemType, val = 'mapinfo')
        self.mapinfoDict = self.dialogDict[mapInfoId] 
        
        self.panel = self._mapinfoPanel()
     
        self._layout(self.panel)



    def _mapinfoPanel(self):
        panel = wx.Panel(parent = self, id = wx.ID_ANY, size = (-1, -1), style = wx.TAB_TRAVERSAL)
        #panel.SetupScrolling(scroll_x = False, scroll_y = True)
        border = wx.BoxSizer(wx.VERTICAL)
        
        
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
        self.colors['borderColor'].SetColour(self.convertRGB(self.mapinfoDict['border']) 
                                            if self.mapinfoDict['border'] != 'none' else 'black')
        self.colors['backgroundColor'].SetColour(self.convertRGB(self.mapinfoDict['background']) 
                                            if self.mapinfoDict['background'] != 'none' else 'black')
        
        flexSizer.Add(self.colors['borderCtrl'], proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        flexSizer.Add(self.colors['borderColor'], proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        flexSizer.Add(self.colors['backgroundCtrl'], proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        flexSizer.Add(self.colors['backgroundColor'], proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        
        sizer.Add(item = flexSizer, proportion = 1, flag = wx.ALL | wx.EXPAND, border = 1)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        panel.SetSizer(border)
        

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
                           
                    
    def OnOK(self, event):
        self.update()
        event.Skip()
        
    def update(self):

        #units
        currUnit = self.units['unitsCtrl'].GetStringSelection()
        self.mapinfoDict['unit'] = currUnit
        # position
        x = self.position['xCtrl'].GetValue() if self.position['xCtrl'].GetValue() else self.mapinfoDict['where'][0]
        y = self.position['yCtrl'].GetValue() if self.position['yCtrl'].GetValue() else self.mapinfoDict['where'][1]
        x = self.unitConv.convert(value = float(self.position['xCtrl'].GetValue()), fromUnit = currUnit, toUnit = 'inch')
        y = self.unitConv.convert(value = float(self.position['yCtrl'].GetValue()), fromUnit = currUnit, toUnit = 'inch')
        self.mapinfoDict['where'] = (x, y)
        # font
        font = self.font['fontCtrl'].GetSelectedFont()
        self.mapinfoDict['font'] = font.GetFaceName()
        self.mapinfoDict['fontsize'] = font.GetPointSize()
        #colors
        self.mapinfoDict['color'] = self.convertRGB(self.font['colorCtrl'].GetColour())
        self.mapinfoDict['background'] = (self.convertRGB(self.colors['backgroundColor'].GetColour())
                                        if self.colors['backgroundCtrl'].GetValue() else 'none') 
        self.mapinfoDict['border'] = (self.convertRGB(self.colors['borderColor'].GetColour())
                                        if self.colors['borderCtrl'].GetValue() else 'none')
        
        # estimation of size
        w = self.mapinfoDict['fontsize'] * 15 
        h = self.mapinfoDict['fontsize'] * 5
        width = self.unitConv.convert(value = w, fromUnit = 'point', toUnit = 'inch')
        height = self.unitConv.convert(value = h, fromUnit = 'point', toUnit = 'inch')
        self.mapinfoDict['rect'] = Rect(x = x, y = y, width = width, height = height)
        
    def getInfo(self):
        return self.mapinfoDict 
        
        
class TextDialog(PsmapDialog):
    def __init__(self, parent, settings, itemType, textId):
        PsmapDialog.__init__(self, parent = parent, title = "Text settings", settings = settings, itemType = itemType)
        self.mapId = find_key(dic = self.itemType, val = 'map')
        if self.mapId is None:
            self.mapId = find_key(dic = self.itemType, val = 'initMap')
        self.textDict = self.dialogDict[textId]
        self.textDict['east'], self.textDict['north'] = PaperMapCoordinates(self, mapId = self.mapId, x = self.textDict['where'][0], y = self.textDict['where'][1], paperToMap = True)
        
        notebook = wx.Notebook(parent = self, id = wx.ID_ANY, style = wx.BK_DEFAULT)     
        self.textPanel = self._textPanel(notebook)
        self.positionPanel = self._positionPanel(notebook)
        self.OnBackground(None)
        self.OnHighlight(None)
        self.OnBorder(None)
        self.OnPositionType(None)
        self.OnRotation(None)
     
        self._layout(notebook)

    def _textPanel(self, notebook):
        panel = wx.Panel(parent = notebook, id = wx.ID_ANY, style = wx.TAB_TRAVERSAL)
        notebook.AddPage(page = panel, text = _("Text"))
        
        border = wx.BoxSizer(wx.VERTICAL)
        
        # text entry
        
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Text")))
        sizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)
        
        textLabel = wx.StaticText(panel, id = wx.ID_ANY, label = _("Enter text:"))
        self.textCtrl = ExpandoTextCtrl(panel, id = wx.ID_ANY, value = self.textDict['text'])
        
        sizer.Add(textLabel, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL|wx.ALL, border = 5)
        sizer.Add(self.textCtrl, proportion = 1, flag = wx.ALIGN_CENTER_VERTICAL|wx.ALL, border = 5)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)        
        

        #font
        
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Font settings")))
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        flexGridSizer = wx.FlexGridSizer (rows = 2, cols = 2, hgap = 5, vgap = 5)
        flexGridSizer.AddGrowableCol(1)
        
        self.AddFont(parent = panel, dialogDict = self.textDict)
        
        flexGridSizer.Add(self.font['fontLabel'], proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        flexGridSizer.Add(self.font['fontCtrl'], proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        flexGridSizer.Add(self.font['colorLabel'], proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)        
        flexGridSizer.Add(self.font['colorCtrl'], proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        
        sizer.Add(item = flexGridSizer, proportion = 1, flag = wx.ALL | wx.EXPAND, border = 1)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        #text effects
        
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Text effects")))
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        gridBagSizer = wx.GridBagSizer (hgap = 5, vgap = 5)
        
        self.effect = {}
        self.effect['backgroundCtrl'] = wx.CheckBox(panel, id = wx.ID_ANY, label = _("text background"))
        self.effect['backgroundColor'] = wx.ColourPickerCtrl(panel, id = wx.ID_ANY)
        
        self.effect['highlightCtrl'] = wx.CheckBox(panel, id = wx.ID_ANY, label = _("highlight"))
        self.effect['highlightColor'] = wx.ColourPickerCtrl(panel, id = wx.ID_ANY)
        self.effect['highlightWidth'] = wx.SpinCtrl(panel, id = wx.ID_ANY, size = self.spinCtrlSize, value = 'pts',min = 0, max = 5, initial = 1)
        self.effect['highlightWidthLabel'] = wx.StaticText(panel, id = wx.ID_ANY, label = _("Width (pts):"))
        
        self.effect['borderCtrl'] = wx.CheckBox(panel, id = wx.ID_ANY, label = _("text border"))
        self.effect['borderColor'] = wx.ColourPickerCtrl(panel, id = wx.ID_ANY)
        self.effect['borderWidth'] = wx.SpinCtrl(panel, id = wx.ID_ANY, size = self.spinCtrlSize, value = 'pts',min = 1, max = 25, initial = 1)
        self.effect['borderWidthLabel'] = wx.StaticText(panel, id = wx.ID_ANY, label = _("Width (pts):"))
        #set values
        self.effect['backgroundCtrl'].SetValue(True if self.textDict['background'] != 'none' else False)
        self.effect['backgroundColor'].SetColour(self.convertRGB(self.textDict['background']) 
                                            if self.textDict['background'] != 'none' else 'white')
        self.effect['highlightCtrl'].SetValue(True if self.textDict['hcolor'] != 'none' else False)
        self.effect['highlightColor'].SetColour(self.convertRGB(self.textDict['hcolor']) 
                                            if self.textDict['hcolor'] != 'none' else 'grey')
        self.effect['highlightWidth'].SetValue(float(self.textDict['hwidth']))
        self.effect['borderCtrl'].SetValue(True if self.textDict['border'] != 'none' else False)
        self.effect['borderColor'].SetColour(self.convertRGB(self.textDict['border']) 
                                            if self.textDict['border'] != 'none' else 'black')
        self.effect['borderWidth'].SetValue(float(self.textDict['width']))
        
        gridBagSizer.Add(self.effect['backgroundCtrl'], pos = (0,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.effect['backgroundColor'], pos = (0,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.effect['highlightCtrl'], pos = (1,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.effect['highlightColor'], pos = (1,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.effect['highlightWidthLabel'], pos = (1,2), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.effect['highlightWidth'], pos = (1,3), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.effect['borderCtrl'], pos = (2,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.effect['borderColor'], pos = (2,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.effect['borderWidthLabel'], pos = (2,2), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.effect['borderWidth'], pos = (2,3), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        
        sizer.Add(item = gridBagSizer, proportion = 1, flag = wx.ALL | wx.EXPAND, border = 1)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        self.Bind(EVT_ETC_LAYOUT_NEEDED, self.OnRefit, self.textCtrl)
        self.Bind(wx.EVT_CHECKBOX, self.OnBackground, self.effect['backgroundCtrl'])
        self.Bind(wx.EVT_CHECKBOX, self.OnHighlight, self.effect['highlightCtrl'])
        self.Bind(wx.EVT_CHECKBOX, self.OnBorder, self.effect['borderCtrl'])
        
        panel.SetSizer(border)
        panel.Fit()
        return panel 
    def _positionPanel(self, notebook):
        panel = wx.Panel(parent = notebook, id = wx.ID_ANY, style = wx.TAB_TRAVERSAL)
        notebook.AddPage(page = panel, text = _("Position"))

        border = wx.BoxSizer(wx.VERTICAL) 

        #Position
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Position")))
        sizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)
        gridBagSizer = wx.GridBagSizer(hgap = 5, vgap = 5)
        gridBagSizer.AddGrowableCol(0)
        gridBagSizer.AddGrowableCol(1)
        
        self.positionLabel = wx.StaticText(panel, id = wx.ID_ANY, label = _("Position is given:"))
        self.paperPositionCtrl = wx.RadioButton(panel, id = wx.ID_ANY, label = _("relatively to paper"), style = wx.RB_GROUP)
        self.mapPositionCtrl = wx.RadioButton(panel, id = wx.ID_ANY, label = _("by map coordinates"))
        self.paperPositionCtrl.SetValue(self.textDict['XY'])
        self.mapPositionCtrl.SetValue(not self.textDict['XY'])
        
        gridBagSizer.Add(self.positionLabel, pos = (0,0), span = (1,3), flag = wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT, border = 0)
        gridBagSizer.Add(self.paperPositionCtrl, pos = (1,0), flag = wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT, border = 0)
        gridBagSizer.Add(self.mapPositionCtrl, pos = (1,1),flag = wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT, border = 0)
        
        # first box - paper coordinates
        box1   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = "")
        sizerP = wx.StaticBoxSizer(box1, wx.VERTICAL)
        self.gridBagSizerP = wx.GridBagSizer (hgap = 5, vgap = 5)
        self.gridBagSizerP.AddGrowableCol(1)
        self.gridBagSizerP.AddGrowableRow(3)
        
        self.AddPosition(parent = panel, dialogDict = self.textDict)
        self.position['comment'].SetLabel(_("Position from the top left\nedge of the paper"))
        self.AddUnits(parent = panel, dialogDict = self.textDict)
        self.gridBagSizerP.Add(self.units['unitsLabel'], pos = (0,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        self.gridBagSizerP.Add(self.units['unitsCtrl'], pos = (0,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        self.gridBagSizerP.Add(self.position['xLabel'], pos = (1,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        self.gridBagSizerP.Add(self.position['xCtrl'], pos = (1,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        self.gridBagSizerP.Add(self.position['yLabel'], pos = (2,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        self.gridBagSizerP.Add(self.position['yCtrl'], pos = (2,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        self.gridBagSizerP.Add(self.position['comment'], pos = (3,0), span = (1,2), flag = wx.ALIGN_BOTTOM, border = 0)
        
        
        sizerP.Add(self.gridBagSizerP, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        gridBagSizer.Add(sizerP, pos = (2,0),span = (1,1), flag = wx.ALIGN_CENTER_HORIZONTAL|wx.EXPAND, border = 0)
        
        
        # second box - map coordinates
        box2   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = "")
        sizerM = wx.StaticBoxSizer(box2, wx.VERTICAL)
        self.gridBagSizerM = wx.GridBagSizer (hgap = 5, vgap = 5)
        self.gridBagSizerM.AddGrowableCol(0)
        self.gridBagSizerM.AddGrowableCol(1)
        
        self.eastingLabel  = wx.StaticText(panel, id = wx.ID_ANY, label = "E:")
        self.northingLabel  = wx.StaticText(panel, id = wx.ID_ANY, label = "N:")
        self.eastingCtrl = wx.TextCtrl(panel, id = wx.ID_ANY, value = "")
        self.northingCtrl = wx.TextCtrl(panel, id = wx.ID_ANY, value = "")
        east, north = PaperMapCoordinates(self, mapId = self.mapId, x = self.textDict['where'][0], y = self.textDict['where'][1], paperToMap = True)
        self.eastingCtrl.SetValue(str(east))
        self.northingCtrl.SetValue(str(north))
        

        self.gridBagSizerM.Add(self.eastingLabel, pos = (0,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        self.gridBagSizerM.Add(self.northingLabel, pos = (1,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        self.gridBagSizerM.Add(self.eastingCtrl, pos = (0,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        self.gridBagSizerM.Add(self.northingCtrl, pos = (1,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        
        sizerM.Add(self.gridBagSizerM, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        gridBagSizer.Add(sizerM, pos = (2,1), flag = wx.ALIGN_LEFT|wx.EXPAND, border = 0)
        
        #offset
        box3   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Offset")))
        sizerO = wx.StaticBoxSizer(box3, wx.VERTICAL)
        gridBagSizerO = wx.GridBagSizer (hgap = 5, vgap = 5)
        self.xoffLabel = wx.StaticText(panel, id = wx.ID_ANY, label = _("horizontal (pts):"))
        self.yoffLabel = wx.StaticText(panel, id = wx.ID_ANY, label = _("vertical (pts):"))
        self.xoffCtrl = wx.SpinCtrl(panel, id = wx.ID_ANY, size = (50, -1), min = -50, max = 50, initial = 0)
        self.yoffCtrl = wx.SpinCtrl(panel, id = wx.ID_ANY, size = (50, -1), min = -50, max = 50, initial = 0) 
        self.xoffCtrl.SetValue(self.textDict['xoffset'])       
        self.yoffCtrl.SetValue(self.textDict['yoffset'])
        gridBagSizerO.Add(self.xoffLabel, pos = (0,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizerO.Add(self.yoffLabel, pos = (1,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizerO.Add(self.xoffCtrl, pos = (0,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizerO.Add(self.yoffCtrl, pos = (1,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        
        sizerO.Add(gridBagSizerO, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        gridBagSizer.Add(sizerO, pos = (3,0), flag = wx.ALIGN_CENTER_HORIZONTAL|wx.EXPAND, border = 0)
        # reference point
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_(" Reference point")))
        sizerR = wx.StaticBoxSizer(box, wx.VERTICAL)
        flexSizer = wx.FlexGridSizer(rows = 3, cols = 3, hgap = 5, vgap = 5)
        flexSizer.AddGrowableCol(0)
        flexSizer.AddGrowableCol(1)
        flexSizer.AddGrowableCol(2)
        ref = []
        for row in ["upper", "center", "lower"]:
            for col in ["left", "center", "right"]:
                ref.append(row + " " + col)
        self.radio = [wx.RadioButton(panel, id = wx.ID_ANY, label = '', style = wx.RB_GROUP, name = ref[0])]
        self.radio[0].SetValue(False)
        flexSizer.Add(self.radio[0], proportion = 0, flag = wx.ALIGN_CENTER, border = 0)
        for i in range(1,9):
            self.radio.append(wx.RadioButton(panel, id = wx.ID_ANY, label = '', name = ref[i]))
            self.radio[-1].SetValue(False)
            flexSizer.Add(self.radio[-1], proportion = 0, flag = wx.ALIGN_CENTER, border = 0)
        self.FindWindowByName(self.textDict['ref']).SetValue(True)

        
        sizerR.Add(flexSizer, proportion = 1, flag = wx.EXPAND, border = 0)
        gridBagSizer.Add(sizerR, pos = (3,1), flag = wx.ALIGN_LEFT|wx.EXPAND, border = 0)
        
        sizer.Add(gridBagSizer, proportion = 1, flag = wx.ALIGN_CENTER_VERTICAL|wx.ALL, border = 5)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
                
        #rotation
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Text rotation")))
        sizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)

        self.rotCtrl = wx.CheckBox(panel, id = wx.ID_ANY, label = _("rotate text (counterclockwise)"))
        self.rotValue = wx.SpinCtrl(panel, wx.ID_ANY, size = (50, -1), min = 0, max = 360, initial = 0)
        if self.textDict['rotate']:
            self.rotValue.SetValue(int(self.textDict['rotate']))
            self.rotCtrl.SetValue(True)
        else:
            self.rotValue.SetValue(0)
            self.rotCtrl.SetValue(False)
        sizer.Add(self.rotCtrl, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT|wx.ALL, border = 5)
        sizer.Add(self.rotValue, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT|wx.ALL, border = 5)
        
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        panel.SetSizer(border)
        panel.Fit()
          
        self.Bind(wx.EVT_RADIOBUTTON, self.OnPositionType, self.paperPositionCtrl) 
        self.Bind(wx.EVT_RADIOBUTTON, self.OnPositionType, self.mapPositionCtrl)
        self.Bind(wx.EVT_CHECKBOX, self.OnRotation, self.rotCtrl)
        
        return panel
     
    def OnRefit(self, event):
        self.Fit()
        
    def OnRotation(self, event):
        if self.rotCtrl.GetValue():
            self.rotValue.Enable()
        else: 
            self.rotValue.Disable()
            
    def OnPositionType(self, event):
        if self.paperPositionCtrl.GetValue():
            for widget in self.gridBagSizerP.GetChildren():
                widget.GetWindow().Enable()
            for widget in self.gridBagSizerM.GetChildren():
                widget.GetWindow().Disable()
        else:
            for widget in self.gridBagSizerM.GetChildren():
                widget.GetWindow().Enable()
            for widget in self.gridBagSizerP.GetChildren():
                widget.GetWindow().Disable()
    def OnBackground(self, event):
        if self.effect['backgroundCtrl'].GetValue():
            self.effect['backgroundColor'].Enable()
        else:
            self.effect['backgroundColor'].Disable()
    
    def OnHighlight(self, event):
        if self.effect['highlightCtrl'].GetValue():
            self.effect['highlightColor'].Enable()
            self.effect['highlightWidth'].Enable()
            self.effect['highlightWidthLabel'].Enable()
        else:
            self.effect['highlightColor'].Disable()
            self.effect['highlightWidth'].Disable()
            self.effect['highlightWidthLabel'].Disable()
            
    def OnBorder(self, event):
        if self.effect['borderCtrl'].GetValue():
            self.effect['borderColor'].Enable()
            self.effect['borderWidth'].Enable()
            self.effect['borderWidthLabel'].Enable()
        else:
            self.effect['borderColor'].Disable()
            self.effect['borderWidth'].Disable()
            self.effect['borderWidthLabel'].Disable()
            
    def update(self): 
        #text
        self.textDict['text'] = self.textCtrl.GetValue()
        if not self.textDict['text']:
            wx.MessageBox(_("No text entered!"), _("Error"))
            return False
            
        #font
        font = self.font['fontCtrl'].GetSelectedFont()
        self.textDict['font'] = font.GetFaceName()
        self.textDict['fontsize'] = font.GetPointSize()
        self.textDict['color'] = self.convertRGB(self.font['colorCtrl'].GetColour())
        #effects
        self.textDict['background'] = (self.convertRGB(self.effect['backgroundColor'].GetColour())
                                        if self.effect['backgroundCtrl'].GetValue() else 'none') 
        self.textDict['border'] = (self.convertRGB(self.effect['borderColor'].GetColour())
                                        if self.effect['borderCtrl'].GetValue() else 'none')
        self.textDict['width'] = self.effect['borderWidth'].GetValue()
        self.textDict['hcolor'] = (self.convertRGB(self.effect['highlightColor'].GetColour())
                                        if self.effect['highlightCtrl'].GetValue() else 'none')
        self.textDict['hwidth'] = self.effect['highlightWidth'].GetValue()
        
        #offset
        self.textDict['xoffset'] = self.xoffCtrl.GetValue()
        self.textDict['yoffset'] = self.yoffCtrl.GetValue()
        #position
        if self.paperPositionCtrl.GetValue():
            self.textDict['XY'] = True
            currUnit = self.units['unitsCtrl'].GetStringSelection()
            self.textDict['unit'] = currUnit
            x = self.position['xCtrl'].GetValue() if self.position['xCtrl'].GetValue() else self.textDict['where'][0]
            y = self.position['yCtrl'].GetValue() if self.position['yCtrl'].GetValue() else self.textDict['where'][1]
            x = self.unitConv.convert(value = float(x), fromUnit = currUnit, toUnit = 'inch')
            y = self.unitConv.convert(value = float(y), fromUnit = currUnit, toUnit = 'inch')
            self.textDict['where'] = x, y
            self.textDict['east'], self.textDict['north'] = PaperMapCoordinates(self, self.mapId, x, y, paperToMap = True)
        else:
            self.textDict['XY'] = False
            self.textDict['east'] = self.eastingCtrl.GetValue() if self.eastingCtrl.GetValue() else self.textDict['east']
            self.textDict['north'] = self.northingCtrl.GetValue() if self.northingCtrl.GetValue() else self.textDict['north']
            self.textDict['where'] = PaperMapCoordinates(self, mapId = self.mapId, x = float(self.textDict['east']),
                                                            y = float(self.textDict['north']), paperToMap = False)
        #rotation
        if self.rotCtrl.GetValue():
            self.textDict['rotate'] = self.rotValue.GetValue()
        else:
            self.textDict['rotate'] = None
        #reference point
        for radio in self.radio:
            if radio.GetValue() == True:
                self.textDict['ref'] = radio.GetName()
        return True

    def OnOK(self, event):
        ok = self.update()
        if ok:
            event.Skip()
        
    def getInfo(self):
        return self.textDict 
    
    
    
    
def find_key(dic, val, multiple = False):
    """!Return the key of dictionary given the value"""
    result = [k for k, v in dic.iteritems() if v == val]
    if len(result) == 0 and not multiple:
        return None
    return sorted(result) if multiple else result[0]

def PaperMapCoordinates(self, mapId, x, y, paperToMap = True):
    """!Converts paper (inch) coordinates -> map coordinates"""
    unitConv = UnitConversion(self)
    currRegionDict = grass.region()
    cornerEasting, cornerNorthing = currRegionDict['w'], currRegionDict['n']
    xMap = self.dialogDict[mapId]['rect'][0]
    yMap = self.dialogDict[mapId]['rect'][1]
    currScale = float(self.dialogDict[mapId]['scale'])

    
    if not paperToMap:
        textEasting, textNorthing = x, y
        eastingDiff = textEasting - cornerEasting 
        eastingDiff = - eastingDiff if currRegionDict['w'] > currRegionDict['e'] else eastingDiff
        northingDiff = textNorthing - cornerNorthing
        northingDiff = - northingDiff if currRegionDict['n'] > currRegionDict['s'] else northingDiff
        xPaper = xMap + unitConv.convert(value = eastingDiff, fromUnit = 'meter', toUnit = 'inch') * currScale
        yPaper = yMap + unitConv.convert(value = northingDiff, fromUnit = 'meter', toUnit = 'inch') * currScale
        return xPaper, yPaper
    else:
        eastingDiff = (x - xMap) if currRegionDict['w'] < currRegionDict['e'] else (xMap - x)
        northingDiff = (y - yMap) if currRegionDict['n'] < currRegionDict['s'] else (yMap - y)
        textEasting = cornerEasting + unitConv.convert(value = eastingDiff, fromUnit = 'inch', toUnit = 'meter') / currScale
        textNorthing = cornerNorthing + unitConv.convert(value = northingDiff, fromUnit = 'inch', toUnit = 'meter') / currScale
        return int(textEasting), int(textNorthing)
    
    
def AutoAdjust(self, scaleType, raster):
    """!Computes map scale and map frame rectangle to fit region (scale is not fixed)"""
    
    mapId = find_key(dic = self.itemType, val = 'map', multiple = False)
    if not mapId:
        return None, None
    
    if scaleType == 0 and raster: # automatic, region from raster
        res = grass.read_command("g.region", flags = 'gu', rast = raster)
        currRegionDict = grass.parse_key_val(res, val_type = float)
    elif scaleType == 1 and self.selectedRaster: # automatic, current region
        currRegionDict = self.currentRegionDict
    else:
        return None, None
    
    rX = self.dialogDict[mapId]['rect'].x
    rY = self.dialogDict[mapId]['rect'].y
    rW = self.dialogDict[mapId]['rect'].width
    rH = self.dialogDict[mapId]['rect'].height
    if not hasattr(self, 'unitConv'):
        self.unitConv = UnitConversion(self)
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
    return scale, Rect(x, y, rWNew, rHNew) #inch

def ComputeSetRegion(self):
    """!Computes and sets region from current scale, map center coordinates and map rectangle"""
    mapId = find_key(dic = self.itemType, val = 'map', multiple = False)
    if mapId and self.dialogDict[mapId]['scaleType'] == 2: # fixed scale
        mapDict = self.dialogDict[mapId]
        scale = mapDict['scale']
            
        if not hasattr(self, 'unitConv'):
            self.unitConv = UnitConversion(self)
        
        rectHalfInch = ( mapDict['rect'].width/2, mapDict['rect'].height/2)
        rectHalfMeter = ( self.unitConv.convert(value = rectHalfInch[0], fromUnit = 'inch', toUnit = 'meter')/scale,
                                self.unitConv.convert(value = rectHalfInch[1], fromUnit = 'inch', toUnit = 'meter')/scale) 

        centerE = mapDict['center'][0]
        centerN = mapDict['center'][1]

        RunCommand('g.region', n = int(centerN + rectHalfMeter[1]),
                       s = int(centerN - rectHalfMeter[1]),
                       e = int(centerE + rectHalfMeter[0]),
                       w = int(centerE - rectHalfMeter[0]),
                       rast = mapDict['raster'])