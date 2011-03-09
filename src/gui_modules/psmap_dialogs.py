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
from math import ceil, floor
from copy import deepcopy

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
from wx.lib.mixins.listctrl import CheckListCtrlMixin, ListCtrlAutoWidthMixin
from wx.lib.expando import ExpandoTextCtrl, EVT_ETC_LAYOUT_NEEDED

try:
    from agw import flatnotebook as fnb
except ImportError: # if it's not there locally, try the wxPython lib.
    import wx.lib.agw.flatnotebook as fnb


class UnitConversion():
    """! Class for converting units"""
    def __init__(self, parent):
        self.parent = parent
        ppi = wx.PaintDC(self.parent).GetPPI()
        self._unitsPage = { 'inch' : 1.0,
                            'point' : 72.0,
                            'centimeter' : 2.54,
                            'milimeter' : 25.4}
        self._unitsMap = {  'meters' : 0.0254,
                            'kilometers' : 2.54e-5,
                            'feet' : 1./12,
                            'miles' : 1./63360,
                            'nautical miles' : 1/72913.44}

        self._units = { 'pixel': ppi[0],
                        'meter': 0.0254,
                        'degrees' : 0.0254  #like 1 meter, incorrect
                        }
        self._units.update(self._unitsPage)
        self._units.update(self._unitsMap)

    def getPageUnits(self):
        return sorted(self._unitsPage.keys())
    
    def getMapUnits(self):
        return sorted(self._unitsMap.keys())
    
    def getAllUnits(self):
        return sorted(self._units.keys())
    
    def convert(self, value, fromUnit = None, toUnit = None):
        return float(value)/self._units[fromUnit]*self._units[toUnit]
    
    
class TCValidator(wx.PyValidator):
    """!validates input in textctrls, combobox, taken from wxpython demo"""
    def __init__(self, flag = None):
        wx.PyValidator.__init__(self)
        self.flag = flag
        self.Bind(wx.EVT_CHAR, self.OnChar)

    def Clone(self):
        return TCValidator(self.flag)

    def Validate(self, win):
       
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
        if self.flag == 'DIGIT_ONLY' and chr(key) in string.digits + '.':
            event.Skip()
            return
##        if self.flag == 'SCALE' and chr(key) in string.digits + ':':
##            event.Skip()
##            return
        if self.flag == 'ZERO_AND_ONE_ONLY' and chr(key) in '01':
            event.Skip()
            return
        if not wx.Validator_IsSilent():
            wx.Bell()
        # Returning without calling even.Skip eats the event before it
        # gets to the text control
        return  


class PenStyleComboBox(wx.combo.OwnerDrawnComboBox):
    """!Combo for selecting line style, taken from wxpython demo"""

    # Overridden from OwnerDrawnComboBox, called to draw each
    # item in the list
    def OnDrawItem(self, dc, rect, item, flags):
        if item == wx.NOT_FOUND:
            # painting the control, but there is no valid item selected yet
            return

        r = wx.Rect(*rect)  # make a copy
        r.Deflate(3, 5)

        penStyle = wx.SOLID
        if item == 1:
            penStyle = wx.LONG_DASH
        elif item == 2:
            penStyle = wx.DOT
        elif item == 3:
            penStyle = wx.DOT_DASH

        pen = wx.Pen(dc.GetTextForeground(), 3, penStyle)
        dc.SetPen(pen)

        # for painting the items in the popup
        dc.DrawText(self.GetString( item ),
                    r.x + 3,
                    (r.y + 0) + ( (r.height/2) - dc.GetCharHeight() )/2
                    )
        dc.DrawLine( r.x+5, r.y+((r.height/4)*3)+1, r.x+r.width - 5, r.y+((r.height/4)*3)+1 )

           
    def OnDrawBackground(self, dc, rect, item, flags):
        """!Overridden from OwnerDrawnComboBox, called for drawing the
            background area of each item."""
        # If the item is selected, or its item # iseven, or we are painting the
        # combo control itself, then use the default rendering.
        if (item & 1 == 0 or flags & (wx.combo.ODCB_PAINTING_CONTROL |
                                      wx.combo.ODCB_PAINTING_SELECTED)):
            wx.combo.OwnerDrawnComboBox.OnDrawBackground(self, dc, rect, item, flags)
            return

        # Otherwise, draw every other background with different colour.
        bgCol = wx.Colour(240,240,250)
        dc.SetBrush(wx.Brush(bgCol))
        dc.SetPen(wx.Pen(bgCol))
        dc.DrawRectangleRect(rect);

    def OnMeasureItem(self, item):
        """!Overridden from OwnerDrawnComboBox, should return the height
            needed to display an item in the popup, or -1 for default"""
        return 30

    def OnMeasureItemWidth(self, item):
        """!Overridden from OwnerDrawnComboBox.  Callback for item width, or
            -1 for default/undetermined"""
        return -1; # default - will be measured from text width  
    
    
class CheckListCtrl(wx.ListCtrl, CheckListCtrlMixin, ListCtrlAutoWidthMixin):
    """!List control for managing order and labels of vector maps in legend"""
    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, id = wx.ID_ANY, 
                style = wx.LC_REPORT|wx.LC_SINGLE_SEL|wx.BORDER_SUNKEN|wx.LC_VRULES|wx.LC_HRULES)
        CheckListCtrlMixin.__init__(self) 
        ListCtrlAutoWidthMixin.__init__(self)
        
        
        
class PsmapDialog(wx.Dialog):
    def __init__(self, parent, id,  title, settings, itemType, apply = True):
        wx.Dialog.__init__(self, parent = parent, id = wx.ID_ANY, 
                            title = title, size = wx.DefaultSize, style = wx.DEFAULT_DIALOG_STYLE)
        self.apply = apply
        self.id = id
        self.parent = parent
        self.dialogDict = settings
        self.itemType = itemType
        self.unitConv = UnitConversion(self)
        self.spinCtrlSize = (50, -1)

        
    def AddUnits(self, parent, dialogDict):
        parent.units = dict()
        parent.units['unitsLabel'] = wx.StaticText(parent, id = wx.ID_ANY, label = _("Units:"))
        choices = self.unitConv.getPageUnits()
        parent.units['unitsCtrl'] = wx.Choice(parent, id = wx.ID_ANY, choices = choices)  
        parent.units['unitsCtrl'].SetStringSelection(dialogDict['unit'])
          
    def AddPosition(self, parent, dialogDict):
        parent.position = dict()
        parent.position['comment'] = wx.StaticText(parent, id = wx.ID_ANY,\
                    label = _("Position of the top left corner\nfrom the top left edge of the paper"))
        parent.position['xLabel'] = wx.StaticText(parent, id = wx.ID_ANY, label = _("X:"))
        parent.position['yLabel'] = wx.StaticText(parent, id = wx.ID_ANY, label = _("Y:"))
        parent.position['xCtrl'] = wx.TextCtrl(parent, id = wx.ID_ANY, value = str(dialogDict['where'][0]), validator = TCValidator(flag = 'DIGIT_ONLY'))
        parent.position['yCtrl'] = wx.TextCtrl(parent, id = wx.ID_ANY, value = str(dialogDict['where'][1]), validator = TCValidator(flag = 'DIGIT_ONLY'))
        if dialogDict.has_key('unit'):
            x = self.unitConv.convert(value = dialogDict['where'][0], fromUnit = 'inch', toUnit = dialogDict['unit'])
            y = self.unitConv.convert(value = dialogDict['where'][1], fromUnit = 'inch', toUnit = dialogDict['unit'])
            parent.position['xCtrl'].SetValue("{0:5.3f}".format(x))
            parent.position['yCtrl'].SetValue("{0:5.3f}".format(y))
        
    def AddFont(self, parent, dialogDict, color = True):
        parent.font = dict()
        parent.font['fontLabel'] = wx.StaticText(parent, id = wx.ID_ANY, label = _("Choose font:"))
        parent.font['fontCtrl'] = wx.FontPickerCtrl(parent, id = wx.ID_ANY)
        
        parent.font['fontCtrl'].SetSelectedFont(
                        wx.FontFromNativeInfoString(dialogDict['font'] + " " + str(dialogDict['fontsize'])))
        parent.font['fontCtrl'].SetMaxPointSize(50)
        
        if color:
            parent.font['colorLabel'] = wx.StaticText(parent, id = wx.ID_ANY, label = _("Choose color:"))
            parent.font['colorCtrl'] = wx.ColourPickerCtrl(parent, id = wx.ID_ANY, style=wx.FNTP_FONTDESC_AS_LABEL)
            parent.font['colorCtrl'].SetColour(dialogDict['color'])
           
##        parent.font['colorCtrl'].SetColour(convertRGB(dialogDict['color'])) 
           
##        parent.font['fontLabel'] = wx.StaticText(parent, id = wx.ID_ANY, label = _("Font:"))
##        parent.font['fontSizeLabel'] = wx.StaticText(parent, id = wx.ID_ANY, label = _("Font size:"))
##        parent.font['fontSizeUnitLabel'] = wx.StaticText(parent, id = wx.ID_ANY, label = _("points"))
##        parent.font['colorLabel'] = wx.StaticText(parent, id = wx.ID_ANY, label = _("Color:"))
##        fontChoices = [ 'Times-Roman', 'Times-Italic', 'Times-Bold', 'Times-BoldItalic', 'Helvetica',\
##                        'Helvetica-Oblique', 'Helvetica-Bold', 'Helvetica-BoldOblique', 'Courier',\
##                        'Courier-Oblique', 'Courier-Bold', 'Courier-BoldOblique']
##        colorChoices = [  'aqua', 'black', 'blue', 'brown', 'cyan', 'gray', 'green', 'indigo', 'magenta',\
##                        'orange', 'purple', 'red', 'violet', 'white', 'yellow']
##        parent.font['fontCtrl'] = wx.Choice(parent, id = wx.ID_ANY, choices = fontChoices)
##        parent.font['fontCtrl'].SetStringSelection(dialogDict['font'])
##        parent.colorCtrl = wx.Choice(parent, id = wx.ID_ANY, choices = colorChoices)
##        parent.colorCtrl.SetStringSelection(parent.rLegendDict['color'])
##        parent.font['fontSizeCtrl']= wx.SpinCtrl(parent, id = wx.ID_ANY, min = 4, max = 50, initial = 10)
##        parent.font['fontSizeCtrl'].SetValue(dialogDict['fontsize'])
##        parent.font['colorCtrl'] = wx.ColourPickerCtrl(parent, id = wx.ID_ANY)
##        parent.font['colorCtrl'].SetColour(dialogDict['color'])    

       
    def OnApply(self, event):
        ok = self.update()
        if ok:
            self.parent.DialogDataChanged(id = self.id)
            return True 
        else:
            return False
        
    def OnOK(self, event):
        ok = self.OnApply(event)
        if ok:
            event.Skip()
        
    def OnCancel(self, event):
        event.Skip()
        
        
    def _layout(self, panel):
        #buttons
        btnCancel = wx.Button(self, wx.ID_CANCEL)
        btnOK = wx.Button(self, wx.ID_OK)
        btnOK.SetDefault()
        if self.apply:
            btnApply = wx.Button(self, wx.ID_APPLY)
        

        # bindigs
        btnOK.Bind(wx.EVT_BUTTON, self.OnOK)
        btnOK.SetToolTipString(_("Close dialog and apply changes"))
        btnCancel.Bind(wx.EVT_BUTTON, self.OnCancel)
        btnCancel.SetToolTipString(_("Close dialog and ignore changes"))
        if self.apply:
            btnApply.Bind(wx.EVT_BUTTON, self.OnApply)
            btnApply.SetToolTipString(_("Apply changes"))
        
        # sizers
        btnSizer = wx.StdDialogButtonSizer()
        btnSizer.AddButton(btnCancel)
        if self.apply:
            btnSizer.AddButton(btnApply)
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
    def __init__(self, parent, id, settings, itemType):
        PsmapDialog.__init__(self, parent = parent, id = id, title = "Page setup",  settings = settings, itemType = itemType)

        
        self.cat = ['Units', 'Format', 'Orientation', 'Width', 'Height', 'Left', 'Right', 'Top', 'Bottom']
        paperString = RunCommand('ps.map', flags = 'p', read = True)
        self.paperTable = self._toList(paperString) 
        self.unitsList = self.unitConv.getPageUnits()
        pageId = id
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

    
    def update(self):
        self.pageSetupDict['Units'] = self.getCtrl('Units').GetString(self.getCtrl('Units').GetSelection())
        self.pageSetupDict['Format'] = self.paperTable[self.getCtrl('Format').GetSelection()]['Format']
        self.pageSetupDict['Orientation'] = self.getCtrl('Orientation').GetString(self.getCtrl('Orientation').GetSelection())
        for item in self.cat[3:]:
            self.pageSetupDict[item] = self.unitConv.convert(value = float(self.getCtrl(item).GetValue()),
                                        fromUnit = self.pageSetupDict['Units'], toUnit = 'inch')
            

            
    def OnOK(self, event):
        try:
            self.update()
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
    """!Dialog for map frame settings and optionally  raster and vector map selection"""
    def __init__(self, parent, id, settings, itemType,  rect = None, notebook = False):
        PsmapDialog.__init__(self, parent = parent, id = id, title = "", settings = settings, itemType = itemType)
 
        self.isNotebook = notebook
        #notebook
        if self.isNotebook:
            notebook = wx.Notebook(parent = self, id = wx.ID_ANY, style = wx.BK_DEFAULT)
            self.mPanel = MapFramePanel(parent = notebook, id = self.id[0], settings = self.dialogDict, 
                                    itemType = self.itemType,  rect = rect, notebook = True)
            self.id[0] = self.mPanel.getId()
            self.rPanel = RasterPanel(parent = notebook, id = self.id[1], settings = self.dialogDict, 
                                    itemType = self.itemType, notebook = True)
            self.id[1] = self.rPanel.getId()
            self.vPanel = VectorPanel(parent = notebook, id = self.id[2], settings = self.dialogDict, itemType = self.itemType)
            self.id[2] = self.vPanel.getId()
            self._layout(notebook)
            self.SetTitle(_("Map settings"))
        else:
            self.mPanel = MapFramePanel(parent = self, id = self.id[0], settings = self.dialogDict, 
                                    itemType = self.itemType, rect = rect, notebook = False)
            self.id[0] = self.mPanel.getId()
            self._layout(self.mPanel)
            self.SetTitle(_("Map frame settings"))
        
        
    def OnApply(self, event):
        """!Apply changes"""
        if self.isNotebook:
            ok = self.vPanel.update()
            if ok:
                self.parent.DialogDataChanged(id = self.id[2])
            else:
                return False
            ok = self.rPanel.update()
            if ok:
                self.parent.DialogDataChanged(id = self.id[1])
            else:
                return False
        ok = self.mPanel.update()
        if ok:
            self.parent.DialogDataChanged(id = self.id[0])
            return True 
        
        return False

class MapFramePanel(wx.Panel):
    """!wx.Panel with raster map settings"""
    def __init__(self, parent, id, settings, itemType, rect, notebook = True):
        wx.Panel.__init__(self, parent, id = wx.ID_ANY, style = wx.TAB_TRAVERSAL)

        self.id = id
        self.itemType = itemType
        self.dialogDict = settings
        if notebook:
            self.book = parent
            self.book.AddPage(page = self, text = _("Map frame"))
            self.mapDialog = self.book.GetParent()
        else:
            self.mapDialog = parent
            
        if self.id is not None:
            self.mapFrameDict = self.dialogDict[self.id] 
        else:
            self.mapFrameDict = self.mapDialog.parent.GetDefault('map')
            self.mapFrameDict['rect'] = rect
            self.id = wx.NewId()
            
        self._layout()

        self.scale = [None]*3
        self.center = [None]*3
        
        
        
        self.selectedMap = self.mapFrameDict['map']
        self.selectedRegion = self.mapFrameDict['region']
        self.scaleType = self.mapFrameDict['scaleType']
        self.mapType = self.mapFrameDict['mapType']
        self.scaleChoice.SetSelection(self.mapFrameDict['scaleType'])
        if self.mapFrameDict['scaleType'] == 0 and self.mapFrameDict['map']:
            self.select.SetValue(self.mapFrameDict['map'])
            if self.mapFrameDict['mapType'] == 'raster':
                self.rasterTypeRadio.SetValue(True)
                self.vectorTypeRadio.SetValue(False)
            else:
                self.rasterTypeRadio.SetValue(False)
                self.vectorTypeRadio.SetValue(True)
        elif self.mapFrameDict['scaleType'] == 1 and self.mapFrameDict['region']:
            self.select.SetValue(self.mapFrameDict['region'])
        
        
        self.OnMap(None)
        self.scale[self.mapFrameDict['scaleType']] = self.mapFrameDict['scale']
        self.center[self.mapFrameDict['scaleType']] = self.mapFrameDict['center']
        self.OnScaleChoice(None)
        self.OnElementType(None)
        self.OnBorder(None)
        
        
        
    def _layout(self):
        """!Do layout"""
        border = wx.BoxSizer(wx.VERTICAL)
        
        box   = wx.StaticBox (parent = self, id = wx.ID_ANY, label = " {0} ".format(_("Map frame")))        
        sizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)
        gridBagSizer = wx.GridBagSizer(hgap = 5, vgap = 5)


        #scale options
        frameText = wx.StaticText(self, id = wx.ID_ANY, label = _("Map frame options:"))
        scaleChoices = [_("fit frame to match selected map"),
                        _("fit frame to match saved region"),
                        _("fixed scale and map center")]
        self.scaleChoice = wx.Choice(self, id = wx.ID_ANY, choices = scaleChoices)
        
        
        gridBagSizer.Add(frameText, pos = (0, 0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.scaleChoice, pos = (1, 0), flag = wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border = 0)
        
        #map and region selection
        self.staticBox = wx.StaticBox (parent = self, id = wx.ID_ANY, label = " {0} ".format(_("Map selection")))        
        sizerM = wx.StaticBoxSizer(self.staticBox, wx.HORIZONTAL)
        self.mapSizer = wx.GridBagSizer(hgap = 5, vgap = 5)

        self.rasterTypeRadio = wx.RadioButton(self, id = wx.ID_ANY, label = " {0} ".format(_("raster")), style = wx.RB_GROUP)
        self.vectorTypeRadio = wx.RadioButton(self, id = wx.ID_ANY, label = " {0} ".format(_("vector")))
        
        self.mapOrRegionText = [_("Map:"), _("Region:")] 
        dc = wx.PaintDC(self)# determine size of labels
        width = max(dc.GetTextExtent(self.mapOrRegionText[0])[0], dc.GetTextExtent(self.mapOrRegionText[1])[0])
        self.mapText = wx.StaticText(self, id = wx.ID_ANY, label = self.mapOrRegionText[0], size = (width, -1))
        self.select = Select(self, id = wx.ID_ANY,# size = globalvar.DIALOG_GSELECT_SIZE,
                             type = 'raster', multiple = False,
                             updateOnPopup = True, onPopup = None)
                            
        self.mapSizer.Add(self.rasterTypeRadio, pos = (0, 1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        self.mapSizer.Add(self.vectorTypeRadio, pos = (0, 2), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        self.mapSizer.Add(self.mapText, pos = (1, 0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        self.mapSizer.Add(self.select, pos = (1, 1), span = (1, 2), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
                 
        sizerM.Add(self.mapSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        gridBagSizer.Add(sizerM, pos = (2, 0), flag = wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border = 0)
        

        #map scale and center
        boxC   = wx.StaticBox (parent = self, id = wx.ID_ANY, label = " {0} ".format(_("Map scale and center")))        
        sizerC = wx.StaticBoxSizer(boxC, wx.HORIZONTAL)
        self.centerSizer = wx.FlexGridSizer(rows = 2, cols = 5, hgap = 5, vgap = 5)        
                
                           
        centerText = wx.StaticText(self, id = wx.ID_ANY, label = _("Center:"))
        self.eastingText = wx.StaticText(self, id = wx.ID_ANY, label = _("E:"))
        self.northingText = wx.StaticText(self, id = wx.ID_ANY, label = _("N:"))
        self.eastingTextCtrl = wx.TextCtrl(self, id = wx.ID_ANY, style = wx.TE_RIGHT, validator = TCValidator(flag = 'DIGIT_ONLY'))
        self.northingTextCtrl = wx.TextCtrl(self, id = wx.ID_ANY, style = wx.TE_RIGHT, validator = TCValidator(flag = 'DIGIT_ONLY'))
        scaleText = wx.StaticText(self, id = wx.ID_ANY, label = _("Scale:"))
        scalePrefixText = wx.StaticText(self, id = wx.ID_ANY, label = _("1 :"))
        self.scaleTextCtrl = wx.TextCtrl(self, id = wx.ID_ANY, value = "", style = wx.TE_RIGHT, validator = TCValidator('DIGIT_ONLY'))
        
        self.centerSizer.Add(centerText, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, border = 10)
        self.centerSizer.Add(self.eastingText, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border = 0)
        self.centerSizer.Add(self.eastingTextCtrl, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        self.centerSizer.Add(self.northingText, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border = 0)
        self.centerSizer.Add(self.northingTextCtrl, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        
        self.centerSizer.Add(scaleText, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, border = 10)
        self.centerSizer.Add(scalePrefixText, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border = 0)
        self.centerSizer.Add(self.scaleTextCtrl, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        
        sizerC.Add(self.centerSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        gridBagSizer.Add(sizerC, pos = (3, 0), flag = wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border = 0)
        
        sizer.Add(gridBagSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        # border
        box   = wx.StaticBox (parent = self, id = wx.ID_ANY, label = " {0} ".format(_("Border")))        
        sizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)
        gridBagSizer = wx.GridBagSizer(hgap = 5, vgap = 5)
        
        self.borderCheck = wx.CheckBox(self, id = wx.ID_ANY, label = (_("draw border around map frame")))
        self.borderCheck.SetValue(True if self.mapFrameDict['border'] == 'y' else False)
        
        self.borderColorText = wx.StaticText(self, id = wx.ID_ANY, label = _("border color:"))
        self.borderWidthText = wx.StaticText(self, id = wx.ID_ANY, label = _("border width (pts):"))
        self.borderColourPicker = wx.ColourPickerCtrl(self, id = wx.ID_ANY)
        self.borderWidthCtrl = wx.SpinCtrl(self, id = wx.ID_ANY, min = 1, max = 100, initial = 1)
        
        if self.mapFrameDict['border'] == 'y':
            self.borderWidthCtrl.SetValue(int(self.mapFrameDict['width']))
            self.borderColourPicker.SetColour(convertRGB(self.mapFrameDict['color']))
        
        
        gridBagSizer.Add(self.borderCheck, pos = (0, 0), span = (1,2), flag = wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border = 0)
        gridBagSizer.Add(self.borderColorText, pos = (1, 1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.borderWidthText, pos = (2, 1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.borderColourPicker, pos = (1, 2), flag = wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border = 0)
        gridBagSizer.Add(self.borderWidthCtrl, pos = (2, 2), flag = wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border = 0)
        
        sizer.Add(gridBagSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        self.SetSizer(border)
        self.Fit()
        
        
        if projInfo()['proj'] == 'll':
            self.scaleChoice.SetItems(self.scaleChoice.GetItems()[0:2])
            boxC.Hide()
            for each in self.centerSizer.GetChildren():
                each.GetWindow().Hide()

            
        # bindings
        self.scaleChoice.Bind(wx.EVT_CHOICE, self.OnScaleChoice)
        self.select.GetTextCtrl().Bind(wx.EVT_TEXT, self.OnMap)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnElementType, self.vectorTypeRadio)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnElementType, self.rasterTypeRadio)
        self.Bind(wx.EVT_CHECKBOX, self.OnBorder, self.borderCheck)
        
        
      
    def RegionDict(self, scaleType):
        """!Returns region dictionary according to selected type of scale"""
        if scaleType == 0 and self.selectedMap: # automatic, region from raster
            if self.rasterTypeRadio.GetValue():# raster or vector
                res = grass.read_command("g.region", flags = 'gu', rast = self.selectedMap)
            else:
                res = grass.read_command("g.region", flags = 'gu', vect = self.selectedMap)
            return grass.parse_key_val(res, val_type = float)
        
        elif scaleType == 1 and self.selectedRegion: # saved region
            res = grass.read_command("g.region", flags = 'gu', region = self.selectedRegion)
            return grass.parse_key_val(res, val_type = float)
        
        return None

    def RegionCenter(self, regionDict):
        """!Returnes map center coordinates of given region dictionary"""
        
        if regionDict:
            cE = (regionDict['w'] + regionDict['e'])/2
            cN = (regionDict['n'] + regionDict['s'])/2
            return cE, cN
        return None
    
    def OnMap(self, event):
        """!Selected map or region changing"""
        
        self.selected = self.select.GetValue() if self.select.GetValue() else None
        if self.scaleChoice.GetSelection() == 0:
            self.selectedMap = self.selected
            mapType = 'raster' if self.rasterTypeRadio.GetValue() else 'vector'
            self.scale[0], foo = AutoAdjust(self, scaleType = 0, map = self.selected,
                                                mapType = mapType, rect = self.mapFrameDict['rect'])
            self.center[0] = self.RegionCenter(self.RegionDict(scaleType = 0))
        elif self.scaleChoice.GetSelection() == 1:
            self.selectedRegion = self.selected
            self.scale[1], foo = AutoAdjust(self, scaleType = 1, region = self.selected, rect = self.mapFrameDict['rect'])
            self.center[1] = self.RegionCenter(self.RegionDict(scaleType = 1))
        else:
            self.scale[2] = None        
            self.center[2] = None
            
        self.OnScaleChoice(None)
        
            
    def OnScaleChoice(self, event):
        """!Selected scale type changing"""
        
        scaleType = self.scaleChoice.GetSelection()
        if self.scaleType != scaleType:
            self.scaleType = scaleType
            self.select.SetValue("")
        
        if scaleType in (0, 1): # automatic - region from raster map, saved region
            if scaleType == 0:
                # set map selection
                self.rasterTypeRadio.Show()
                self.vectorTypeRadio.Show()
                self.staticBox.SetLabel(" {0} ".format(_("Map selection")))
                type = 'raster' if self.rasterTypeRadio.GetValue() else 'vector'
                self.select.SetElementList(type = type)
                self.mapText.SetLabel(self.mapOrRegionText[0])
                self.select.SetToolTipString(_("Region is set to match this map,\nraster or vector map must be added later"))
                    
            if scaleType == 1:
                # set region selection
                self.rasterTypeRadio.Hide()
                self.vectorTypeRadio.Hide()
                self.staticBox.SetLabel(" {0} ".format(_("Region selection")))
                type = 'region'
                self.select.SetElementList(type = type)
                self.mapText.SetLabel(self.mapOrRegionText[1])
                self.select.SetToolTipString(_(""))
                
            for each in self.mapSizer.GetChildren():
                each.GetWindow().Enable()
            for each in self.centerSizer.GetChildren():
                each.GetWindow().Disable()
                    
            if self.scale[scaleType]:
                self.scaleTextCtrl.SetValue("{0:.0f}".format(1/self.scale[scaleType]))
            if self.center[scaleType]:
                self.eastingTextCtrl.SetValue(str(self.center[scaleType][0]))
                self.northingTextCtrl.SetValue(str(self.center[scaleType][1]))
        else: # fixed
            for each in self.mapSizer.GetChildren():
                each.GetWindow().Disable()
            for each in self.centerSizer.GetChildren():
                each.GetWindow().Enable()
                    
            if self.scale[scaleType]:
                self.scaleTextCtrl.SetValue("{0:.0f}".format(1/self.scale[scaleType]))
            if self.center[scaleType]:
                self.eastingTextCtrl.SetValue(str(self.center[scaleType][0]))
                self.northingTextCtrl.SetValue(str(self.center[scaleType][1]))
                
    def OnElementType(self, event):
        """!Changes data in map selection tree ctrl popup"""
        if self.rasterTypeRadio.GetValue():
            mapType = 'raster'
        else:
            mapType = 'vector'
        self.select.SetElementList(type  = mapType)
        if self.mapType != mapType and event is not None:
            self.mapType = mapType
            self.select.SetValue('')
        self.mapType = mapType    
        
    def OnBorder(self, event):
        """!Enables/disable the part relating to border of map frame"""
        for each in (self.borderColorText, self.borderWidthText, self.borderColourPicker, self.borderWidthCtrl):
            each.Enable(self.borderCheck.GetValue())
            
    def getId(self):
        """!Returns id of raster map"""
        return self.id
            
    def update(self):
        """!Save changes"""
        mapFrameDict = dict(self.mapFrameDict)
        
        #scale
        scaleType = self.scaleType
        mapFrameDict['scaleType'] = scaleType
        
        if mapFrameDict['scaleType'] == 0:
            if self.select.GetValue():
                mapFrameDict['map'] = self.select.GetValue()
                mapFrameDict['mapType'] = self.mapType
                mapFrameDict['region'] = None

                self.scale[0], self.rectAdjusted = AutoAdjust(self, scaleType = 0, map = mapFrameDict['map'],
                                                                   mapType = self.mapType, rect = self.mapFrameDict['rect'])
                                               
                mapFrameDict['rect'] = self.rectAdjusted if self.rectAdjusted else self.mapFrameDict['rect']
                mapFrameDict['scale'] = self.scale[0]
                
                mapFrameDict['center'] = self.center[scaleType]
                # set region
                if self.mapType == 'raster':
                    RunCommand('g.region', rast = mapFrameDict['map'])
                if self.mapType == 'vector':
                    rasterId = find_key(dic = self.itemType, val = 'raster')
                    if rasterId:
                        RunCommand('g.region', vect = mapFrameDict['map'], rast = self.dialogDict[rasterId]['raster'])
                    else:
                        RunCommand('g.region', vect = mapFrameDict['map'])
            else:
                wx.MessageBox(message = _("No map selected!"),
                                    caption = _('Invalid input'), style = wx.OK|wx.ICON_ERROR)
                return False    
            
        elif mapFrameDict['scaleType'] == 1:
            if self.select.GetValue():
                mapFrameDict['map'] = None
                mapFrameDict['mapType'] = None
                mapFrameDict['region'] = self.select.GetValue()
                self.scale[1], self.rectAdjusted = AutoAdjust(self, scaleType = 1, region = mapFrameDict['region'],
                                                                                rect = self.mapFrameDict['rect'])
                mapFrameDict['rect'] = self.rectAdjusted if self.rectAdjusted else self.mapFrameDict['rect']
                mapFrameDict['scale'] = self.scale[scaleType]
                mapFrameDict['center'] = self.center[scaleType]
                # set region
                RunCommand('g.region', region = mapFrameDict['region'])
            else:
                wx.MessageBox(message = _("No region selected!"),
                                    caption = _('Invalid input'), style = wx.OK|wx.ICON_ERROR)
                return False 
                               
            
        elif scaleType == 2:
            mapFrameDict['map'] = None
            mapFrameDict['mapType'] = None
            mapFrameDict['region'] = None
            mapFrameDict['rect'] = self.mapFrameDict['rect']
            try:
                scaleNumber = float(self.scaleTextCtrl.GetValue())
                centerE = float(self.eastingTextCtrl.GetValue()) 
                centerN = float(self.northingTextCtrl.GetValue())
            except ValueError, SyntaxError:
                wx.MessageBox(message = _("Invalid scale or map center!"),
                                    caption = _('Invalid input'), style = wx.OK|wx.ICON_ERROR)
                return False  
            mapFrameDict['scale'] = 1/scaleNumber
            mapFrameDict['center'] = centerE, centerN
        
            ComputeSetRegion(self, mapDict = mapFrameDict)
        
        # border
        mapFrameDict['border'] = 'y' if self.borderCheck.GetValue() else 'n'
        if mapFrameDict['border'] == 'y':
            mapFrameDict['width'] = self.borderWidthCtrl.GetValue()
            mapFrameDict['color'] = convertRGB(self.borderColourPicker.GetColour())
            
        
        
        self.dialogDict[self.id] = mapFrameDict
        self.itemType[self.id] = 'map'
        if self.id not in self.mapDialog.parent.objectId:
            self.mapDialog.parent.objectId.insert(0, self.id)# map frame is drawn first
        return True
        
class RasterPanel(wx.Panel):
    """!Panel for raster map settings"""
    def __init__(self, parent, id, settings, itemType, notebook = True):
        wx.Panel.__init__(self, parent, id = wx.ID_ANY, style = wx.TAB_TRAVERSAL)
        self.itemType = itemType
        self.dialogDict = settings
        
        if notebook:
            self.book = parent
            self.book.AddPage(page = self, text = _("Raster map"))
            self.mainDialog = self.book.GetParent()
        else:
            self.mainDialog = parent
        if id:
            self.id = id
            self.rasterDict = self.dialogDict[self.id]
        else:
            self.id = wx.NewId()
            self.rasterDict = dict(self.mainDialog.parent.GetDefault('raster'))
         
        self._layout()
        self.OnRaster(None)
            
    def _layout(self):
        """!Do layout"""
        border = wx.BoxSizer(wx.VERTICAL)
        
        # choose raster map
        
        box   = wx.StaticBox (parent = self, id = wx.ID_ANY, label = " {0} ".format(_("Choose raster map")))
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        gridBagSizer = wx.GridBagSizer (hgap = 5, vgap = 5)
        
        self.rasterNoRadio = wx.RadioButton(self, id = wx.ID_ANY, label = _("no raster map"), style = wx.RB_GROUP)
        self.rasterYesRadio = wx.RadioButton(self, id = wx.ID_ANY, label = _("raster:"))
        
        self.rasterSelect = Select(self, id = wx.ID_ANY, size = globalvar.DIALOG_GSELECT_SIZE,
                             type = 'raster', multiple = False,
                             updateOnPopup = True, onPopup = None)
        if self.rasterDict['isRaster']:
            self.rasterYesRadio.SetValue(True)
            self.rasterNoRadio.SetValue(False)
            self.rasterSelect.SetValue(self.rasterDict['raster'])
        else:
            self.rasterYesRadio.SetValue(False)
            self.rasterNoRadio.SetValue(True)
            mapId = find_key(dic = self.itemType, val = 'map')
            if self.dialogDict[mapId]['map'] and self.dialogDict[mapId]['mapType'] == 'raster':
                self.rasterSelect.SetValue(self.dialogDict[mapId]['map'])# raster map from map frame dialog if possible
            else:
                self.rasterSelect.SetValue('')                
        gridBagSizer.Add(self.rasterNoRadio, pos = (0, 0), span = (1, 2), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)            
        gridBagSizer.Add(self.rasterYesRadio, pos = (1, 0),  flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.rasterSelect, pos = (1, 1), flag = wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border = 0)
        
        sizer.Add(gridBagSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        #self.rasterSelect.GetTextCtrl().Bind(wx.EVT_TEXT, self.OnRaster)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnRaster, self.rasterNoRadio)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnRaster, self.rasterYesRadio)
        
        self.SetSizer(border)
        self.Fit()
        
    def OnRaster(self, event):
        """!Enable/disable raster selection"""
        self.rasterSelect.Enable(self.rasterYesRadio.GetValue())
        
    def update(self):
        #draw raster
        if self.rasterNoRadio.GetValue() or not self.rasterSelect.GetValue():
            self.rasterDict['isRaster'] = False
            self.rasterDict['raster'] = None
            if self.id in self.dialogDict:
                del self.dialogDict[self.id]
                del self.itemType[self.id]
        else:
            self.rasterDict['isRaster'] = True
            self.rasterDict['raster'] = self.rasterSelect.GetValue()
            self.dialogDict[self.id] = self.rasterDict
            self.itemType[self.id] = 'raster'
            

        return True
        
    def getId(self):
        return self.id
  
class VectorPanel(wx.Panel):
    """!Panel for vector maps settings"""
    def __init__(self, parent, id, settings, itemType, notebook = True):
        wx.Panel.__init__(self, parent, id = wx.ID_ANY, style = wx.TAB_TRAVERSAL)
        self.itemType = itemType
        self.dialogDict = settings
        self.tmpDialogDict = {}
        ids = find_key(dic = self.itemType, val = 'vProperties', multiple = True)
        for i in ids:
            self.tmpDialogDict[i] = dict(self.dialogDict[i])
        self.parent = parent
        if id:
            self.id = id
            self.vectorList = deepcopy(self.dialogDict[id]['list'])
        else:
            self.id = wx.NewId()
            self.vectorList = []
        
        self.vLegendId = find_key(dic = self.itemType, val = 'vectorLegend')
         
        self._layout()
        
        if notebook:
            self.parent.AddPage(page = self, text = _("Vector maps"))
            
    def _layout(self):
        """!Do layout"""
        border = wx.BoxSizer(wx.VERTICAL)
        
        # choose vector map
        
        box   = wx.StaticBox (parent = self, id = wx.ID_ANY, label = " {0} ".format(_("Choose map")))
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        gridBagSizer = wx.GridBagSizer (hgap = 5, vgap = 5)
        
        text = wx.StaticText(self, id = wx.ID_ANY, label = _("Map:"))
        self.select = Select(self, id = wx.ID_ANY,# size = globalvar.DIALOG_GSELECT_SIZE,
                             type = 'vector', multiple = False,
                             updateOnPopup = True, onPopup = None)
        topologyType = [_("points"), _("lines"), _("areas")]
        self.vectorType = wx.RadioBox(self, id = wx.ID_ANY, label = " {0} ".format(_("Data Type")), choices = topologyType,
                                        majorDimension = 3, style = wx.RA_SPECIFY_COLS)
        self.AddVector = wx.Button(self, id = wx.ID_ANY, label = _("Add"))
        
        gridBagSizer.Add(text, pos = (0,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.select, pos = (0,1), span = (1, 2), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.vectorType, pos = (1,1), flag = wx.ALIGN_CENTER, border = 0)
        gridBagSizer.Add(self.AddVector, pos = (1,2), flag = wx.ALIGN_BOTTOM|wx.ALIGN_RIGHT, border = 0)
        
        sizer.Add(gridBagSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        # manage vector layers
        
        box   = wx.StaticBox (parent = self, id = wx.ID_ANY, label = " {0} ".format(_("Vector maps order")))
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        gridBagSizer = wx.GridBagSizer (hgap = 5, vgap = 5)
        gridBagSizer.AddGrowableCol(0,2)
        gridBagSizer.AddGrowableCol(1,1)

        
        
        text = wx.StaticText(self, id = wx.ID_ANY, label = _("The topmost vector map overlaps the others"))
        self.listbox = wx.ListBox(self, id = wx.ID_ANY, choices = [], style = wx.LB_SINGLE|wx.LB_NEEDED_SB)
        self.btnUp = wx.Button(self, id = wx.ID_ANY, label = _("Up"))
        self.btnDown = wx.Button(self, id = wx.ID_ANY, label = _("Down"))
        self.btnDel = wx.Button(self, id = wx.ID_ANY, label = _("Delete"))
        self.btnProp = wx.Button(self, id = wx.ID_ANY, label = _("Properties"))
        
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
        self.select.GetTextCtrl().Bind(wx.EVT_TEXT, self.OnVector)
        
        self.SetSizer(border)
        self.Fit()

    def OnVector(self, event):
        """!Gets info about toplogy and enables/disables choices point/line/area"""
        vmap = self.select.GetValue()        
        topoInfo = grass.parse_key_val(RunCommand('v.info', read = True, map = vmap, shell = 'topo'), val_type = int)

        self.vectorType.EnableItem(2, bool(topoInfo['areas']))
        self.vectorType.EnableItem(1, bool(topoInfo['boundaries']) or bool(topoInfo['lines']))
        self.vectorType.EnableItem(0, bool(topoInfo['centroids'] or bool(topoInfo['points']) ))
        for item in range(2,-1,-1):
            if self.vectorType.IsItemEnabled(item):
                self.vectorType.SetSelection(item)
                break
        
        self.AddVector.SetFocus()        
            
    def OnAddVector(self, event):
        """!Adds vector map to list"""
        vmap = self.select.GetValue()
        if vmap:
            mapname = vmap.split('@')[0]
            try:
                mapset = '(' + vmap.split('@')[1] + ')'
            except IndexError:
                mapset = ''
            type = self.vectorType.GetStringSelection()
            record = "{0} - {1}".format(vmap,type)
            id = wx.NewId()
            lpos = 1
            label = mapname + mapset 
            self.vectorList.insert(0, [vmap, type, id, lpos, label])
            self.reposition()
            self.listbox.InsertItems([record], 0)
            self.tmpDialogDict[id] = dict(self.DefaultData(dataType = type))
            self.listbox.SetSelection(0)  
            self.listbox.EnsureVisible(0)
            self.btnProp.SetFocus()
            
    def OnDelete(self, event):
        """!Deletes vector map from the list"""
        if self.listbox.GetSelections():
            pos = self.listbox.GetSelection()
            id = self.vectorList[pos][2]
            del self.vectorList[pos]
            del self.tmpDialogDict[id]
            for i in range(pos, len(self.vectorList)):
                if self.vectorList[i][3]:# can be 0
                    self.vectorList[i][3] -= 1
            self.updateListBox(selected = pos if pos < len(self.vectorList) -1 else len(self.vectorList) -1)
            
    def OnUp(self, event):
        """!Moves selected map to top"""
        if self.listbox.GetSelections():
            pos = self.listbox.GetSelection()
            if pos:
                self.vectorList.insert(pos - 1, self.vectorList.pop(pos))
            if not self.vLegendId:
                self.reposition()
            self.updateListBox(selected = (pos - 1) if pos > 0 else 0)
            
    def OnDown(self, event):
        """!Moves selected map to bottom"""
        if self.listbox.GetSelections():
            pos = self.listbox.GetSelection()
            if pos != len(self.vectorList) - 1:
                self.vectorList.insert(pos + 1, self.vectorList.pop(pos))
                if not self.vLegendId:
                    self.reposition()
            self.updateListBox(selected = (pos + 1) if pos < len(self.vectorList) -1 else len(self.vectorList) -1)
    
    def OnProperties(self, event):
        """!Opens vector map properties dialog"""
        if self.listbox.GetSelections():
            pos = self.listbox.GetSelection()
            id = self.vectorList[pos][2]

            dlg = VPropertiesDialog(self, id = id, settings = self.dialogDict, itemType = self.itemType,
                                    vectors = self.vectorList, tmpSettings = self.tmpDialogDict[id])
            dlg.ShowModal()
            
            self.parent.FindWindowById(wx.ID_OK).SetFocus()
           
    def DefaultData(self, dataType):
        """!Default data for vector properties dialogs, depends on data type(points, lines, areas)"""
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
                        fcolor = 'none', rgbcolumn = None,
                        pat = None, pwidth = 1, scale = 1)
        return dd
    
    def updateListBox(self, selected = None):
        mapList = ["{0} - {1}".format(*item) for item in self.vectorList]
        self.listbox.Set(mapList)
        if selected is not None:
            self.listbox.SetSelection(selected)  
            self.listbox.EnsureVisible(selected)  
              
    def reposition(self):
        """!Update position in legend, used only if there is no vlegend yet"""
        for i in range(len(self.vectorList)):
            if self.vectorList[i][3]:
                self.vectorList[i][3] = i + 1
                
    def getId(self):
        return self.id
        
    def update(self):
        ids = find_key(dic = self.itemType, val = 'vProperties', multiple = True)
        for id in ids:
            del self.itemType[id]
            del self.dialogDict[id]
            
        if len(self.vectorList) > 0:
            self.dialogDict[self.id] = {'list': deepcopy(self.vectorList)}
            self.itemType[self.id] = 'vector'

            # save new vectors
            for item in self.vectorList:
                id = item[2]
                self.itemType[id] = 'vProperties'
                self.dialogDict[id] = dict(self.tmpDialogDict[id])
            
        else:
            if self.dialogDict.has_key(self.id):
                del self.dialogDict[self.id]
                del self.itemType[self.id]
        return True
    
class RasterDialog(PsmapDialog):
    def __init__(self, parent, id, settings, itemType):
        PsmapDialog.__init__(self, parent = parent, id = id, title = "Choose raster map", settings = settings, itemType = itemType)

        self.rPanel = RasterPanel(parent = self, id = self.id, settings = self.dialogDict, itemType = self.itemType, notebook = False)

        self.id = self.rPanel.getId()
        self._layout(self.rPanel)
    
    def update(self):
        self.rPanel.update()
        
    def OnApply(self, event):
        self.update()
        mapId = find_key(dic = self.itemType, val = 'map')# need to redraw labels on map frame
        self.parent.DialogDataChanged(id = mapId)
        return True
 
class MainVectorDialog(PsmapDialog):
    def __init__(self, parent, id, settings, itemType):
        PsmapDialog.__init__(self, parent = parent, id = id, title = "Choose vector maps", settings = settings, itemType = itemType)

        self.vPanel = VectorPanel(parent = self, id = self.id, settings = self.dialogDict, itemType = self.itemType, notebook = False)

        self.id = self.vPanel.getId()
        self._layout(self.vPanel)
    
    def update(self):
        self.vPanel.update()
        
    def OnApply(self, event):
        self.update()
        mapId = find_key(dic = self.itemType, val = 'map')# need to redraw labels on map frame
        self.parent.DialogDataChanged(id = mapId)
        return True
        

class VPropertiesDialog(PsmapDialog):
    def __init__(self, parent, id, settings, itemType, vectors, tmpSettings):
        PsmapDialog.__init__(self, parent = parent, id = id, title = "", settings = settings, itemType = itemType, apply = False)
        
        vectorList = vectors
        self.vPropertiesDict = tmpSettings
        
        # determine map and its type
        for item in vectorList:
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
        self.colorPicker.SetColour(convertRGB(self.vPropertiesDict['color']) if self.vPropertiesDict['color'] != 'none' else 'black')
        
        
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
        self.fillColorPicker.SetColour(convertRGB(self.vPropertiesDict['fcolor']) if self.vPropertiesDict['fcolor'] != 'none' else 'red')
        
        
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
        self.colorPicker.SetColour(convertRGB(self.vPropertiesDict['hcolor']) if self.vPropertiesDict['hcolor'] != 'none' else 'black')
        
        
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
        self.fillColorPicker.SetColour(convertRGB(self.vPropertiesDict['color']) if self.vPropertiesDict['color'] != 'none' else 'black')
        
        
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
        
        widthText = wx.StaticText(panel, id = wx.ID_ANY, label = _("Set width (pts):"))
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
        penStyles = ["solid", "dashed", "dotted", "dashdotted"]
        self.styleCombo = PenStyleComboBox(panel, choices = penStyles, validator = TCValidator(flag = 'ZERO_AND_ONE_ONLY'))
##        self.styleCombo = wx.ComboBox(panel, id = wx.ID_ANY,
##                            choices = ["solid", "dashed", "dotted", "dashdotted"],
##                            validator = TCValidator(flag = 'ZERO_AND_ONE_ONLY'))
##        self.styleCombo.SetToolTipString(_("It's possible to enter a series of 0's and 1's too. "\
##                                    "The first block of repeated zeros or ones represents 'draw', "\
##                                    "the second block represents 'blank'. An even number of blocks "\
##                                    "will repeat the pattern, an odd number of blocks will alternate the pattern."))
        linecapText = wx.StaticText(panel, id = wx.ID_ANY, label = _("Choose linecap:"))
        self.linecapChoice = wx.Choice(panel, id = wx.ID_ANY, choices = ["butt", "round", "extended_butt"])
        
        self.styleCombo.SetValue(self.vPropertiesDict['style'])
        self.linecapChoice.SetStringSelection(self.vPropertiesDict['linecap'])
        
        gridBagSizer.Add(styleText, pos = (0, 0),  flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.styleCombo, pos = (0, 1), flag = wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border = 0)
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
        self.patWidthText = wx.StaticText(panel, id = wx.ID_ANY, label = _("pattern line width (pts):"))
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
        
    def update(self):
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
                self.vPropertiesDict['color'] = convertRGB(self.colorPicker.GetColour())
                self.vPropertiesDict['width'] = self.widthSpin.GetValue()
            else:
                self.vPropertiesDict['color'] = 'none'
                
            if self.fillCheck.GetValue():
                if self.colorPickerRadio.GetValue():
                    self.vPropertiesDict['fcolor'] = convertRGB(self.fillColorPicker.GetColour())
                    self.vPropertiesDict['rgbcolumn'] = None
                if self.colorColRadio.GetValue():
                    self.vPropertiesDict['fcolor'] = 'none'# this color is taken in case of no record in rgb column
                    self.vPropertiesDict['rgbcolumn'] = self.colorColChoice.GetStringSelection()
            else:
                self.vPropertiesDict['fcolor'] = 'none'    
                
        if self.type == 'lines':
                #hcolor only when no rgbcolumn
            if self.outlineCheck.GetValue():# and self.fillCheck.GetValue() and self.colorColRadio.GetValue():
                self.vPropertiesDict['hcolor'] = convertRGB(self.colorPicker.GetColour())
                self.vPropertiesDict['hwidth'] = self.widthSpin.GetValue()
            else:
                self.vPropertiesDict['hcolor'] = 'none'
                
            if self.colorPickerRadio.GetValue():
                self.vPropertiesDict['color'] = convertRGB(self.fillColorPicker.GetColour())
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
            
    
    def OnOK(self, event):
        self.update()
        event.Skip()
        
class LegendDialog(PsmapDialog):
    def __init__(self, parent, id, settings, itemType, page):
        PsmapDialog.__init__(self, parent = parent, id = id, title = "Legend settings", settings = settings, itemType = itemType)
        
        self.mapId = find_key(dic = self.itemType, val = 'map')
        self.vectorId = find_key(dic = self.itemType, val = 'vector')
        self.rasterId = find_key(dic = self.itemType, val = 'raster')

        self.pageId = find_key(dic = self.itemType, val = 'paper'), find_key(dic = self.itemType, val = 'margins')
        #raster legend
        if self.id[0] is not None:
            self.rLegendDict = self.dialogDict[self.id[0]] 
        else:
            self.rLegendDict = dict(self.parent.GetDefault('rasterLegend'))
            self.id[0] = wx.NewId()
        #vectro legend    
        if self.id[1] is not None:
            self.vLegendDict = self.dialogDict[self.id[1]] 
        else:
            self.vLegendDict = dict(self.parent.GetDefault('vectorLegend'))
            self.id[1] = wx.NewId()
        
        self.currRaster = self.dialogDict[self.rasterId]['raster'] if self.rasterId else None
        
        #notebook
        self.notebook = wx.Notebook(parent = self, id = wx.ID_ANY, style = wx.BK_DEFAULT)
        self.panelRaster = self._rasterLegend(self.notebook)
        self.panelVector = self._vectorLegend(self.notebook)  
        self.OnDefaultSize(None)
        self.OnRaster(None)
        self.OnRange(None)
        self.OnIsLegend(None)
        self.OnSpan(None)
        self.OnBorder(None)
        
        
        self._layout(self.notebook)
        self.notebook.ChangeSelection(page)
        
    def _rasterLegend(self, notebook):
        panel = scrolled.ScrolledPanel(parent = notebook, id = wx.ID_ANY, size = (-1, 500), style = wx.TAB_TRAVERSAL)
        panel.SetupScrolling(scroll_x = False, scroll_y = True)
        notebook.AddPage(page = panel, text = _("Raster legend"))

        border = wx.BoxSizer(wx.VERTICAL)
        # is legend
        self.isRLegend = wx.CheckBox(panel, id = wx.ID_ANY, label = _("Show raster legend"))
        self.isRLegend.SetValue(self.rLegendDict['rLegend'])
        border.Add(item = self.isRLegend, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)

        # choose raster
        
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Source raster")))
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        flexSizer = wx.FlexGridSizer (cols = 2, hgap = 5, vgap = 5)
        flexSizer.AddGrowableCol(1)
        
        self.rasterDefault = wx.RadioButton(panel, id = wx.ID_ANY, label = _("current raster"), style = wx.RB_GROUP)
        self.rasterOther = wx.RadioButton(panel, id = wx.ID_ANY, label = _("select raster"))
        self.rasterDefault.SetValue(self.rLegendDict['rasterDefault'])#
        self.rasterOther.SetValue(not self.rLegendDict['rasterDefault'])#

        rasterType = self.getRasterType(map = self.currRaster)

        self.rasterCurrent = wx.StaticText(panel, id = wx.ID_ANY, label = _("{0}: type {1}").format(self.currRaster, str(rasterType)))
        self.rasterSelect = Select( panel, id = wx.ID_ANY, size = globalvar.DIALOG_GSELECT_SIZE,
                                    type = 'raster', multiple = False,
                                    updateOnPopup = True, onPopup = None)
        self.rasterSelect.SetValue(self.rLegendDict['raster'] if not self.rLegendDict['rasterDefault'] else '')
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
        
        # size, position and font
        self.sizePositionFont(legendType = 'raster', parent = panel, mainSizer = border)
        
        # advanced settings
        
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Advanced legend settings")))
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        gridBagSizer = wx.GridBagSizer (hgap = 5, vgap = 5)
        # no data
        self.nodata = wx.CheckBox(panel, id = wx.ID_ANY, label = _('draw "no data" box'))
        self.nodata.SetValue(True if self.rLegendDict['nodata'] == 'y' else False)
        #tickbar
        self.ticks = wx.CheckBox(panel, id = wx.ID_ANY, label = _("draw ticks across color table"))
        self.ticks.SetValue(True if self.rLegendDict['tickbar'] == 'y' else False)
        # range
        if self.rasterId and self.dialogDict[self.rasterId]['raster']:
            range = RunCommand('r.info', flags = 'r', read = True, map = self.dialogDict[self.rasterId]['raster']).strip().split('\n')
            self.minim, self.maxim = range[0].split('=')[1], range[1].split('=')[1]
        else:
            self.minim, self.maxim = 0,0
        self.range = wx.CheckBox(panel, id = wx.ID_ANY, label = _("range"))
        self.range.SetValue(self.rLegendDict['range'])
        self.minText =  wx.StaticText(panel, id = wx.ID_ANY, label = "{0} ({1})".format(_("min:"),self.minim))
        self.maxText =  wx.StaticText(panel, id = wx.ID_ANY, label = "{0} ({1})".format(_("max:"),self.maxim))
       
        self.min = wx.TextCtrl(panel, id = wx.ID_ANY, value = str(self.rLegendDict['min']))
        self.max = wx.TextCtrl(panel, id = wx.ID_ANY, value = str(self.rLegendDict['max']))
        
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
        self.Bind(wx.EVT_CHECKBOX, self.OnIsLegend, self.isRLegend)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnDiscrete, self.discrete)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnDiscrete, self.continuous)
        self.Bind(wx.EVT_CHECKBOX, self.OnDefaultSize, panel.defaultSize)
        self.Bind(wx.EVT_CHECKBOX, self.OnRange, self.range)
        self.rasterSelect.GetTextCtrl().Bind(wx.EVT_TEXT, self.OnRaster)
        
        return panel
    
    def _vectorLegend(self, notebook):
        panel = scrolled.ScrolledPanel(parent = notebook, id = wx.ID_ANY, size = (-1, 500), style = wx.TAB_TRAVERSAL)
        panel.SetupScrolling(scroll_x = False, scroll_y = True)
        notebook.AddPage(page = panel, text = _("Vector legend"))

        border = wx.BoxSizer(wx.VERTICAL)
        # is legend
        self.isVLegend = wx.CheckBox(panel, id = wx.ID_ANY, label = _("Show vector legend"))
        self.isVLegend.SetValue(self.vLegendDict['vLegend'])
        border.Add(item = self.isVLegend, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        #vector maps, their order, labels
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Source vector maps")))
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        gridBagSizer = wx.GridBagSizer (hgap = 5, vgap = 5)
        gridBagSizer.AddGrowableCol(0,3)
        gridBagSizer.AddGrowableCol(1,1)
        
        vectorText = wx.StaticText(panel, id = wx.ID_ANY, label = _("Choose vector maps and their order in legend"))

        self.vectorListCtrl = CheckListCtrl(panel)
        
        self.vectorListCtrl.InsertColumn(0, _("Vector map"))
        self.vectorListCtrl.InsertColumn(1, _("Label"))
        if self.vectorId:
            vectors = sorted(self.dialogDict[self.vectorId]['list'], key = lambda x: x[3])
            for vector in vectors:
                index = self.vectorListCtrl.InsertStringItem(sys.maxint, vector[0].split('@')[0])
                self.vectorListCtrl.SetStringItem(index, 1, vector[4])
                self.vectorListCtrl.SetItemData(index, index)
                self.vectorListCtrl.CheckItem(index, True)
                if vector[3] == 0:
                    self.vectorListCtrl.CheckItem(index, False)
        self.vectorListCtrl.SetColumnWidth(0, wx.LIST_AUTOSIZE)
        self.vectorListCtrl.SetColumnWidth(1, wx.LIST_AUTOSIZE)
        
        self.btnUp = wx.Button(panel, id = wx.ID_ANY, label = _("Up"))
        self.btnDown = wx.Button(panel, id = wx.ID_ANY, label = _("Down"))
        self.btnLabel = wx.Button(panel, id = wx.ID_ANY, label = _("Edit label"))

        
        gridBagSizer.Add(vectorText, pos = (0,0), span = (1,2), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.vectorListCtrl, pos = (1,0), span = (3,1), flag = wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border = 0)
        gridBagSizer.Add(self.btnUp, pos = (1,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.btnDown, pos = (2,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.btnLabel, pos = (3,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        
        sizer.Add(gridBagSizer, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border = 0)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        # size, position and font
        self.sizePositionFont(legendType = 'vector', parent = panel, mainSizer = border)
         
        # border
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Border")))
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        flexGridSizer = wx.FlexGridSizer(cols = 2, hgap = 5, vgap = 5)
        
        self.borderCheck = wx.CheckBox(panel, id = wx.ID_ANY, label = _("draw border around legend"))
        self.borderColorCtrl = wx.ColourPickerCtrl(panel, id = wx.ID_ANY, style = wx.FNTP_FONTDESC_AS_LABEL)
        if self.vLegendDict['border'] == 'none':
            self.borderColorCtrl.SetColour('black')
            self.borderCheck.SetValue(False)
        else:
            self.borderColorCtrl.SetColour(self.vLegendDict['border'])
            self.borderCheck.SetValue(True)
            
        flexGridSizer.Add(self.borderCheck, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)    
        flexGridSizer.Add(self.borderColorCtrl, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        sizer.Add(item = flexGridSizer, proportion = 1, flag = wx.ALL | wx.EXPAND, border = 1)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        self.Bind(wx.EVT_BUTTON, self.OnUp, self.btnUp)
        self.Bind(wx.EVT_BUTTON, self.OnDown, self.btnDown)  
        self.Bind(wx.EVT_BUTTON, self.OnEditLabel, self.btnLabel)
        self.Bind(wx.EVT_CHECKBOX, self.OnIsLegend, self.isVLegend)    
        self.Bind(wx.EVT_CHECKBOX, self.OnSpan, panel.spanRadio)  
        self.Bind(wx.EVT_CHECKBOX, self.OnBorder, self.borderCheck)
        self.Bind(wx.EVT_FONTPICKER_CHANGED, self.OnFont, panel.font['fontCtrl']) 
        
        panel.SetSizer(border)
        
        panel.Fit()
        return panel
    
    def sizePositionFont(self, legendType, parent, mainSizer):
        """!Insert widgets for size, position and font control"""
        legendDict = self.rLegendDict if legendType == 'raster' else self.vLegendDict
        panel = parent
        border = mainSizer
        
        # size and position
        
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Size and position")))        
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        #unit
        self.AddUnits(parent = panel, dialogDict = legendDict)
        unitBox = wx.BoxSizer(wx.HORIZONTAL)
        unitBox.Add(panel.units['unitsLabel'], proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL|wx.LEFT, border = 10)
        unitBox.Add(panel.units['unitsCtrl'], proportion = 1, flag = wx.ALL, border = 5)
        sizer.Add(unitBox, proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        
        hBox = wx.BoxSizer(wx.HORIZONTAL)
        posBox = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Position"))) 
        posSizer = wx.StaticBoxSizer(posBox, wx.VERTICAL)       
        sizeBox = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Size"))) 
        sizeSizer = wx.StaticBoxSizer(sizeBox, wx.VERTICAL) 
        posGridBagSizer = wx.GridBagSizer(hgap = 10, vgap = 5)
        posGridBagSizer.AddGrowableRow(2)
        
        #position
        self.AddPosition(parent = panel, dialogDict = legendDict)
        
        posGridBagSizer.Add(panel.position['xLabel'], pos = (0,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        posGridBagSizer.Add(panel.position['xCtrl'], pos = (0,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        posGridBagSizer.Add(panel.position['yLabel'], pos = (1,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        posGridBagSizer.Add(panel.position['yCtrl'], pos = (1,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        posGridBagSizer.Add(panel.position['comment'], pos = (2,0), span = (1,2), flag =wx.ALIGN_BOTTOM, border = 0)
        posSizer.Add(posGridBagSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        
        #size
        width = wx.StaticText(panel, id = wx.ID_ANY, label = _("Width:"))
        w = self.unitConv.convert(value = float(legendDict['width']), fromUnit = 'inch', toUnit = legendDict['unit'])
        panel.widthCtrl = wx.TextCtrl(panel, id = wx.ID_ANY, value = str(w), validator = TCValidator("DIGIT_ONLY"))
        
        if legendType == 'raster':
            panel.defaultSize = wx.CheckBox(panel, id = wx.ID_ANY, label = _("Use default size"))
            panel.defaultSize.SetValue(legendDict['defaultSize'])
            
            panel.heightOrColumnsLabel = wx.StaticText(panel, id = wx.ID_ANY, label = _("Height:"))
            h = self.unitConv.convert(value = float(legendDict['height']), fromUnit = 'inch', toUnit = legendDict['unit'])
            panel.heightOrColumnsCtrl = wx.TextCtrl(panel, id = wx.ID_ANY, value = str(h), validator = TCValidator("DIGIT_ONLY"))
            
            self.rSizeGBSizer = wx.GridBagSizer(hgap = 5, vgap = 5)
            self.rSizeGBSizer.Add(panel.defaultSize, pos = (0,0), span = (1,2), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
            self.rSizeGBSizer.Add(width, pos = (1,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
            self.rSizeGBSizer.Add(panel.widthCtrl, pos = (1,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
            self.rSizeGBSizer.Add(panel.heightOrColumnsLabel, pos = (2,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
            self.rSizeGBSizer.Add(panel.heightOrColumnsCtrl, pos = (2,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
            sizeSizer.Add(self.rSizeGBSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
            
        if legendType == 'vector':
            panel.widthCtrl.SetToolTipString(_("Width of the color symbol (for lines)\nin front of the legend text")) 
            #columns
            minVect, maxVect = 0, 0
            if self.vectorId:
                minVect = 1
                maxVect = min(10, len(self.dialogDict[self.vectorId]['list']))
            cols = wx.StaticText(panel, id = wx.ID_ANY, label = _("Columns:"))
            panel.colsCtrl = wx.SpinCtrl(panel, id = wx.ID_ANY, value = "",
                                        min = minVect, max = maxVect, initial = legendDict['cols'])
            #span
            panel.spanRadio = wx.CheckBox(panel, id = wx.ID_ANY, label = _("column span:"))
            panel.spanTextCtrl = wx.TextCtrl(panel, id = wx.ID_ANY, value = '')
            panel.spanTextCtrl.SetToolTipString(_("Column separation distance between the left edges\n"\
                                                "of two columns in a multicolumn legend"))
            if legendDict['span']:
                panel.spanRadio.SetValue(True)
                s = self.unitConv.convert(value = float(legendDict['span']), fromUnit = 'inch', toUnit = legendDict['unit'])    
                panel.spanTextCtrl.SetValue(str(s))
            else:
                panel.spanRadio.SetValue(False)
                
            self.vSizeGBSizer = wx.GridBagSizer(hgap = 5, vgap = 5)
            self.vSizeGBSizer.AddGrowableCol(1)
            self.vSizeGBSizer.Add(width, pos = (0,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
            self.vSizeGBSizer.Add(panel.widthCtrl, pos = (0,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
            self.vSizeGBSizer.Add(cols, pos = (1,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
            self.vSizeGBSizer.Add(panel.colsCtrl, pos = (1,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
            self.vSizeGBSizer.Add(panel.spanRadio, pos = (2,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
            self.vSizeGBSizer.Add(panel.spanTextCtrl, pos = (2,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
            sizeSizer.Add(self.vSizeGBSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)        
        
        hBox.Add(posSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 3)
        hBox.Add(sizeSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 3)
        sizer.Add(hBox, proportion = 0, flag = wx.EXPAND, border = 0)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        
        # font
        
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Font settings")))
        fontSizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        flexSizer = wx.FlexGridSizer (cols = 2, hgap = 5, vgap = 5)
        flexSizer.AddGrowableCol(1)
        
        if legendType == 'raster':
            self.AddFont(parent = panel, dialogDict = legendDict, color = True)
        else:
            self.AddFont(parent = panel, dialogDict = legendDict, color = False)            
        flexSizer.Add(panel.font['fontLabel'], proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        flexSizer.Add(panel.font['fontCtrl'], proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        if legendType == 'raster':
            flexSizer.Add(panel.font['colorLabel'], proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)        
            flexSizer.Add(panel.font['colorCtrl'], proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        
        fontSizer.Add(item = flexSizer, proportion = 1, flag = wx.ALL | wx.EXPAND, border = 1)
        border.Add(item = fontSizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)    
            



    #   some enable/disable methods  
        
    def OnIsLegend(self, event):
        """!Enables and disables controls, it depends if raster or vector legend is checked"""
        page = self.notebook.GetSelection()
        if page == 0 or event is None:
            children = self.panelRaster.GetChildren()
            if self.isRLegend.GetValue():
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
        if page == 1 or event is None:
            children = self.panelVector.GetChildren()
            if self.isVLegend.GetValue():
                for i, widget in enumerate(children):
                        widget.Enable()
                self.OnSpan(None)
                self.OnBorder(None)
            else:
                for i, widget in enumerate(children):
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
            if self.rLegendDict['discrete'] == 'y':
                self.discrete.SetValue(True)
            elif self.rLegendDict['discrete'] == 'n':
                self.continuous.SetValue(True)
        self.OnDiscrete(None)
        
    def OnDiscrete(self, event):
        """! Change control according to the type of legend"""
        enabledSize = self.panelRaster.heightOrColumnsCtrl.IsEnabled()
        self.panelRaster.heightOrColumnsCtrl.Destroy()
        if self.discrete.GetValue():
            self.panelRaster.heightOrColumnsLabel.SetLabel(_("Columns:"))
            self.panelRaster.heightOrColumnsCtrl = wx.SpinCtrl(self.panelRaster, id = wx.ID_ANY, value = "", min = 1, max = 10, initial = self.rLegendDict['cols'])
            self.panelRaster.heightOrColumnsCtrl.Enable(enabledSize)
            self.nodata.Enable()
            self.range.Disable()
            self.min.Disable()
            self.max.Disable()
            self.minText.Disable()
            self.maxText.Disable()
            self.ticks.Disable()
        else:
            self.panelRaster.heightOrColumnsLabel.SetLabel(_("Height:"))
            h = self.unitConv.convert(value = float(self.rLegendDict['height']), fromUnit = 'inch', toUnit = self.rLegendDict['unit'])
            self.panelRaster.heightOrColumnsCtrl = wx.TextCtrl(self.panelRaster, id = wx.ID_ANY,
                                                    value = str(h), validator = TCValidator("DIGIT_ONLY"))
            self.panelRaster.heightOrColumnsCtrl.Enable(enabledSize)
            self.nodata.Disable()
            self.range.Enable()
            if self.range.GetValue():
                self.minText.Enable()
                self.maxText.Enable()
                self.min.Enable()
                self.max.Enable()
            self.ticks.Enable()
        
        self.rSizeGBSizer.Add(self.panelRaster.heightOrColumnsCtrl, pos = (2,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        self.panelRaster.Layout()
        self.panelRaster.Fit()
        
        
    def OnDefaultSize(self, event):
        if self.panelRaster.defaultSize.GetValue():
            self.panelRaster.widthCtrl.Disable()
            self.panelRaster.heightOrColumnsCtrl.Disable()        
        else:    
            self.panelRaster.widthCtrl.Enable()
            self.panelRaster.heightOrColumnsCtrl.Enable()
        
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
     
    def OnUp(self, event):
        """!Moves selected map up, changes order in vector legend"""
        if self.vectorListCtrl.GetFirstSelected() != -1:
            pos = self.vectorListCtrl.GetFirstSelected()
            if pos:
                idx1 = self.vectorListCtrl.GetItemData(pos) - 1
                idx2 = self.vectorListCtrl.GetItemData(pos - 1) + 1
                self.vectorListCtrl.SetItemData(pos, idx1) 
                self.vectorListCtrl.SetItemData(pos - 1, idx2) 
                self.vectorListCtrl.SortItems(cmp)
                selected = (pos - 1) if pos > 0 else 0
                self.vectorListCtrl.Select(selected)
       
    def OnDown(self, event):
        """!Moves selected map down, changes order in vector legend"""
        if self.vectorListCtrl.GetFirstSelected() != -1:
            pos = self.vectorListCtrl.GetFirstSelected()
            if pos != self.vectorListCtrl.GetItemCount() - 1:
                idx1 = self.vectorListCtrl.GetItemData(pos) + 1
                idx2 = self.vectorListCtrl.GetItemData(pos + 1) - 1
                self.vectorListCtrl.SetItemData(pos, idx1) 
                self.vectorListCtrl.SetItemData(pos + 1, idx2) 
                self.vectorListCtrl.SortItems(cmp)
                selected = (pos + 1) if pos < self.vectorListCtrl.GetItemCount() -1 else self.vectorListCtrl.GetItemCount() -1
                self.vectorListCtrl.Select(selected)
                
    def OnEditLabel(self, event):
        """!Change legend label of vector map"""
        if self.vectorListCtrl.GetFirstSelected() != -1:
            idx = self.vectorListCtrl.GetFirstSelected()
            default = self.vectorListCtrl.GetItem(idx, 1).GetText()
            dlg = wx.TextEntryDialog(self, message = _("Edit legend label:"), caption = _("Edit label"),
                                    defaultValue = default, style = wx.OK|wx.CANCEL|wx.CENTRE)
            if dlg.ShowModal() == wx.ID_OK:
                new = dlg.GetValue()
                self.vectorListCtrl.SetStringItem(idx, 1, new)
            dlg.Destroy()
        
    def OnSpan(self, event):
        self.panelVector.spanTextCtrl.Enable(self.panelVector.spanRadio.GetValue())
    def OnFont(self, event):
        """!Changes default width according to fontsize, width [inch] = fontsize[pt]/24"""   
        fontsize = self.panelVector.font['fontCtrl'].GetSelectedFont().GetPointSize() 
        unit = self.panelVector.units['unitsCtrl'].GetStringSelection()
        w = fontsize/24.
        width = self.unitConv.convert(value = w, fromUnit = 'inch', toUnit = unit)
        self.panelVector.widthCtrl.SetValue("{0:3.2f}".format(width))
        
    def OnBorder(self, event):
        """!Enables/disables colorPickerCtrl for border"""    
        self.borderColorCtrl.Enable(self.borderCheck.GetValue())
        
    def updateRasterLegend(self):
        """!Save information from raster legend dialog to dictionary"""

        #is raster legend
        if not self.isRLegend.GetValue():
            self.rLegendDict['rLegend'] = False
        else:
            self.rLegendDict['rLegend'] = True
        #units
        currUnit = self.panelRaster.units['unitsCtrl'].GetStringSelection()
        self.rLegendDict['unit'] = currUnit
        # raster
        if self.rasterDefault.GetValue():
            self.rLegendDict['rasterDefault'] = True
            self.rLegendDict['raster'] = self.currRaster
        else:
            self.rLegendDict['rasterDefault'] = False
            self.rLegendDict['raster'] = self.rasterSelect.GetValue()
        if self.rLegendDict['rLegend'] and not self.rLegendDict['raster']:
            wx.MessageBox(message = _("No raster map selected!"),
                                    caption = _('No raster'), style = wx.OK|wx.ICON_ERROR)
            return False
            
        if self.rLegendDict['raster']:
            # type and range of map
            rasterType = self.getRasterType(self.rLegendDict['raster'])
            self.rLegendDict['type'] = rasterType
            
            range = RunCommand('r.info', flags = 'r', read = True, map = self.rLegendDict['raster']).strip().split('\n')
            minim, maxim = range[0].split('=')[1], range[1].split('=')[1]
            
            #discrete
            if self.discrete.GetValue():
                self.rLegendDict['discrete'] = 'y'
            else:
                self.rLegendDict['discrete'] = 'n'   
                    
            # font 
            font = self.panelRaster.font['fontCtrl'].GetSelectedFont()
            self.rLegendDict['font'] = font.GetFaceName()
            self.rLegendDict['fontsize'] = font.GetPointSize()
            self.rLegendDict['color'] = self.panelRaster.font['colorCtrl'].GetColour().GetAsString(wx.C2S_NAME)
            dc = wx.PaintDC(self)
            dc.SetFont(font)#wx.Font(   pointSize = self.rLegendDict['fontsize'], family = font.GetFamily(),
                                                #style = font.GetStyle(), weight = wx.FONTWEIGHT_NORMAL))
            # position
            x = self.unitConv.convert(value = float(self.panelRaster.position['xCtrl'].GetValue()), fromUnit = currUnit, toUnit = 'inch')
            y = self.unitConv.convert(value = float(self.panelRaster.position['yCtrl'].GetValue()), fromUnit = currUnit, toUnit = 'inch')
            self.rLegendDict['where'] = (x, y)
            # estimated size
            if not self.panelRaster.defaultSize.GetValue():
                self.rLegendDict['defaultSize'] = False
            
                width = self.unitConv.convert(value = float(self.panelRaster.widthCtrl.GetValue()), fromUnit = currUnit, toUnit = 'inch')
                height = self.unitConv.convert(value = float(self.panelRaster.heightOrColumnsCtrl.GetValue()), fromUnit = currUnit, toUnit = 'inch')
            
                if self.rLegendDict['discrete'] == 'n':  #rasterType in ('FCELL', 'DCELL'):
                    self.rLegendDict['width'] = width 
                    self.rLegendDict['height'] = height
                    textPart = self.unitConv.convert(value = dc.GetTextExtent(maxim)[0], fromUnit = 'pixel', toUnit = 'inch')
                    drawWidth = width + textPart
                    drawHeight = height
                    self.rLegendDict['rect'] = wx.Rect2D(x = x, y = y, w = drawWidth, h = drawHeight)
                else: #categorical map
                    self.rLegendDict['width'] = width 
                    self.rLegendDict['cols'] = self.panelRaster.heightOrColumnsCtrl.GetValue() 
                    cat = RunCommand(   'r.category', read = True, map = self.rLegendDict['raster'],
                                        fs = ':').strip().split('\n')
                    rows = ceil(float(len(cat))/self.rLegendDict['cols'])

                    drawHeight = self.unitConv.convert(value =  1.5 *rows * self.rLegendDict['fontsize'], fromUnit = 'point', toUnit = 'inch')
                    self.rLegendDict['rect'] = wx.Rect2D(x = x, y = y, w = width, h = drawHeight)

            else:
                self.rLegendDict['defaultSize'] = True
                if self.rLegendDict['discrete'] == 'n':  #rasterType in ('FCELL', 'DCELL'):
                    textPart = self.unitConv.convert(value = dc.GetTextExtent(maxim)[0], fromUnit = 'pixel', toUnit = 'inch')
                    drawWidth = self.unitConv.convert( value = self.rLegendDict['fontsize'] * 2, 
                                                    fromUnit = 'point', toUnit = 'inch') + textPart
                                
                    drawHeight = self.unitConv.convert(value = self.rLegendDict['fontsize'] * 10,
                                                    fromUnit = 'point', toUnit = 'inch')
                    self.rLegendDict['rect'] = wx.Rect2D(x = x, y = y, w = drawWidth, h = drawHeight)
                else:#categorical map
                    self.rLegendDict['cols'] = self.panelRaster.heightOrColumnsCtrl.GetValue()
                    cat = RunCommand(   'r.category', read = True, map = self.rLegendDict['raster'],
                                        fs = ':').strip().split('\n')
                    if len(cat) == 1:# for discrete FCELL
                        rows = float(maxim)
                    else:
                        rows = ceil(float(len(cat))/self.rLegendDict['cols'])
                    drawHeight = self.unitConv.convert(value =  1.5 *rows * self.rLegendDict['fontsize'],
                                                    fromUnit = 'point', toUnit = 'inch')
                    paperWidth = self.dialogDict[self.pageId]['Width']- self.dialogDict[self.pageId]['Right']\
                                                                        - self.dialogDict[self.pageId]['Left']
                    drawWidth = (paperWidth / self.rLegendDict['cols']) * (self.rLegendDict['cols'] - 1) + 1
                    self.rLegendDict['rect'] = wx.Rect2D(x = x, y = y, w = drawWidth, h = drawHeight)


                         
            # no data
            if self.rLegendDict['discrete'] == 'y':
                if self.nodata.GetValue():
                    self.rLegendDict['nodata'] = 'y'
                else:
                    self.rLegendDict['nodata'] = 'n'
            # tickbar
            elif self.rLegendDict['discrete'] == 'n':
                if self.ticks.GetValue():
                    self.rLegendDict['tickbar'] = 'y'
                else:
                    self.rLegendDict['tickbar'] = 'n'
            # range
                if self.range.GetValue():
                    self.rLegendDict['range'] = True
                    self.rLegendDict['min'] = self.min.GetValue()
                    self.rLegendDict['max'] = self.max.GetValue()
                else:
                    self.rLegendDict['range'] = False
                    
        self.dialogDict[self.id[0]] = self.rLegendDict
        self.itemType[self.id[0]] = 'rasterLegend'
        if self.id[0] not in self.parent.objectId:
            self.parent.objectId.append(self.id[0])
        return True
                    
    def updateVectorLegend(self):
        """!Save information from vector legend dialog to dictionary"""

        #is vector legend
        if not self.isVLegend.GetValue():
            self.vLegendDict['vLegend'] = False
        else:
            self.vLegendDict['vLegend'] = True   
        if self.vLegendDict['vLegend'] == True and self.vectorId is not None:
            # labels
            #reindex order
            idx = 1
            for item in range(self.vectorListCtrl.GetItemCount()):
                if self.vectorListCtrl.IsChecked(item):
                    self.vectorListCtrl.SetItemData(item, idx)
                    idx += 1
                else:
                    self.vectorListCtrl.SetItemData(item, 0)
            if idx == 1: 
                self.vLegendDict['vLegend'] = False     
            else:
                for i, vector in enumerate(self.dialogDict[self.vectorId]['list']):
                    item = self.vectorListCtrl.FindItem(start = -1, str = vector[0].split('@')[0])
                    self.dialogDict[self.vectorId]['list'][i][3] = self.vectorListCtrl.GetItemData(item)
                    self.dialogDict[self.vectorId]['list'][i][4] = self.vectorListCtrl.GetItem(item, 1).GetText()
                
                #units
                currUnit = self.panelVector.units['unitsCtrl'].GetStringSelection()
                self.vLegendDict['unit'] = currUnit
                # position
                x = self.unitConv.convert(value = float(self.panelVector.position['xCtrl'].GetValue()),
                                                                fromUnit = currUnit, toUnit = 'inch')
                y = self.unitConv.convert(value = float(self.panelVector.position['yCtrl'].GetValue()),
                                                                fromUnit = currUnit, toUnit = 'inch')
                self.vLegendDict['where'] = (x, y)
                
                # font 
                font = self.panelVector.font['fontCtrl'].GetSelectedFont()
                self.vLegendDict['font'] = font.GetFaceName()
                self.vLegendDict['fontsize'] = font.GetPointSize()
                dc = wx.PaintDC(self)
                dc.SetFont(font)
                #size
                width = self.unitConv.convert(value = float(self.panelVector.widthCtrl.GetValue()),
                                                        fromUnit = currUnit, toUnit = 'inch')
                self.vLegendDict['width'] = width
                self.vLegendDict['cols'] = self.panelVector.colsCtrl.GetValue()
                if self.panelVector.spanRadio.GetValue() and self.panelVector.spanTextCtrl.GetValue():
                    self.vLegendDict['span'] = self.panelVector.spanTextCtrl.GetValue()
                else:
                    self.vLegendDict['span'] = None
                    
                # size estimation
                vectors = self.dialogDict[self.vectorId]['list']
                labels = [vector[4] for vector in vectors if vector[3] != 0]
                extent = dc.GetTextExtent(max(labels))
                wExtent = self.unitConv.convert(value = extent[0], fromUnit = 'pixel', toUnit = 'inch')
                hExtent = self.unitConv.convert(value = extent[1], fromUnit = 'pixel', toUnit = 'inch')
                w = (width + wExtent) * self.vLegendDict['cols']
                h = len(labels) * hExtent / self.vLegendDict['cols']
                h *= 1.1
                self.vLegendDict['rect'] = wx.Rect2D(x, y, w, h)
                
                #border
                if self.borderCheck.GetValue():
                    self.vLegendDict['border'] = self.borderColorCtrl.GetColour().GetAsString(flags=wx.C2S_NAME)
                else:
                    self.vLegendDict['border'] = 'none'
            
        self.dialogDict[self.id[1]] = self.vLegendDict
        self.itemType[self.id[1]] = 'vectorLegend'
        if self.id[1] not in self.parent.objectId:
            self.parent.objectId.append(self.id[1])
        return True
    
    def update(self)  :
        okR = self.updateRasterLegend()
        okV = self.updateVectorLegend()
        if okR and okV:
            return True
        return False
        
    def getRasterType(self, map):
        rasterType = RunCommand('r.info', flags = 't', read = True, 
                                map = map).strip().split('=')
        return (rasterType[1] if rasterType[0] else None)
        

             
class MapinfoDialog(PsmapDialog):
    def __init__(self, parent, id, settings, itemType):
        PsmapDialog.__init__(self, parent = parent, id = id, title = "Mapinfo settings", settings = settings, itemType = itemType)
        if self.id is not None:
            self.mapinfoDict = self.dialogDict[id] 
        else:
            self.mapinfoDict = dict(self.parent.GetDefault('mapinfo'))
            self.id = wx.NewId()
            
        self.panel = self._mapinfoPanel()
        
        self._layout(self.panel)
        self.OnIsBackground(None)
        self.OnIsBorder(None)


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
        gridBagSizer.Add(panel.units['unitsLabel'], pos = (0,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(panel.units['unitsCtrl'], pos = (0,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(panel.position['xLabel'], pos = (1,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(panel.position['xCtrl'], pos = (1,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(panel.position['yLabel'], pos = (2,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(panel.position['yCtrl'], pos = (2,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(panel.position['comment'], pos = (3,0), span = (1,2), flag =wx.ALIGN_BOTTOM, border = 0)
        
        sizer.Add(gridBagSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        # font
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Font settings")))
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        gridBagSizer = wx.GridBagSizer (hgap = 5, vgap = 5)
        gridBagSizer.AddGrowableCol(1)
        
        self.AddFont(parent = panel, dialogDict = self.mapinfoDict)#creates font color too, used below
        
        gridBagSizer.Add(panel.font['fontLabel'], pos = (0,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(panel.font['fontCtrl'], pos = (0,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(panel.font['colorLabel'], pos = (1,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)        
        gridBagSizer.Add(panel.font['colorCtrl'], pos = (1,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)


        
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
##        self.colors['borderColor'].SetColour(convertRGB(self.mapinfoDict['border']) 
##                                            if self.mapinfoDict['border'] != 'none' else 'black')
        self.colors['backgroundColor'].SetColour(self.mapinfoDict['background']
                                            if self.mapinfoDict['background'] != 'none' else 'black')
##        self.colors['backgroundColor'].SetColour(convertRGB(self.mapinfoDict['background']) 
##                                            if self.mapinfoDict['background'] != 'none' else 'black')
        
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
                           
                    
    def update(self):

        #units
        currUnit = self.panel.units['unitsCtrl'].GetStringSelection()
        self.mapinfoDict['unit'] = currUnit
        # position
        x = self.panel.position['xCtrl'].GetValue() if self.panel.position['xCtrl'].GetValue() else self.mapinfoDict['where'][0]
        y = self.panel.position['yCtrl'].GetValue() if self.panel.position['yCtrl'].GetValue() else self.mapinfoDict['where'][1]
        x = self.unitConv.convert(value = float(self.panel.position['xCtrl'].GetValue()), fromUnit = currUnit, toUnit = 'inch')
        y = self.unitConv.convert(value = float(self.panel.position['yCtrl'].GetValue()), fromUnit = currUnit, toUnit = 'inch')
        self.mapinfoDict['where'] = (x, y)
        # font
        font = self.panel.font['fontCtrl'].GetSelectedFont()
        self.mapinfoDict['font'] = font.GetFaceName()
        self.mapinfoDict['fontsize'] = font.GetPointSize()
        #colors
        self.mapinfoDict['color'] = self.panel.font['colorCtrl'].GetColour().GetAsString(flags=wx.C2S_NAME)
        self.mapinfoDict['background'] = self.colors['backgroundColor'].GetColour().GetAsString(flags=wx.C2S_NAME)\
                                        if self.colors['backgroundCtrl'].GetValue() else 'none'
##        self.mapinfoDict['background'] = (convertRGB(self.colors['backgroundColor'].GetColour())
##                                        if self.colors['backgroundCtrl'].GetValue() else 'none') 
        self.mapinfoDict['border'] = self.colors['borderColor'].GetColour().GetAsString(flags=wx.C2S_NAME)\
                                        if self.colors['borderCtrl'].GetValue() else 'none'
##        self.mapinfoDict['border'] = (convertRGB(self.colors['borderColor'].GetColour())
##                                        if self.colors['borderCtrl'].GetValue() else 'none')
        
        # estimation of size
        w = self.mapinfoDict['fontsize'] * 20 # any better estimation? 
        h = self.mapinfoDict['fontsize'] * 7
        width = self.unitConv.convert(value = w, fromUnit = 'point', toUnit = 'inch')
        height = self.unitConv.convert(value = h, fromUnit = 'point', toUnit = 'inch')
        self.mapinfoDict['rect'] = wx.Rect2D(x = x, y = y, w = width, h = height)
        
        
        self.dialogDict[self.id] = self.mapinfoDict
        self.itemType[self.id] = 'mapinfo'
        if self.id not in self.parent.objectId:
            self.parent.objectId.append(self.id)
            
        return True
      
    
class ScalebarDialog(PsmapDialog):
    """!Dialog for scale bar"""
    def __init__(self, parent, id, settings, itemType):
        PsmapDialog.__init__(self, parent = parent, id = id, title = "Scale bar settings", settings = settings, itemType = itemType)
        if self.id is not None:
            self.scalebarDict = self.dialogDict[id] 
        else:
            self.scalebarDict = dict(self.parent.GetDefault('scalebar'))
            self.id = wx.NewId()
            
        self.panel = self._scalebarPanel()
        
        self._layout(self.panel)
        
        self.mapUnit = projInfo()['units']
        if projInfo()['proj'] == 'xy':
            self.mapUnit = 'meters'
        if self.mapUnit not in self.unitConv.getAllUnits():
            wx.MessageBox(message = _("Units of current projection are not supported,\n meters will be used!"),
                            caption = _('Unsupported units'),
                                    style = wx.OK|wx.ICON_ERROR)
            self.mapUnit = 'meters'
            
    def _scalebarPanel(self):
        panel = wx.Panel(parent = self, id = wx.ID_ANY, style = wx.TAB_TRAVERSAL)
        border = wx.BoxSizer(wx.VERTICAL)
        #        
        # position
        #
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Position")))
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        gridBagSizer = wx.GridBagSizer (hgap = 5, vgap = 5)
        gridBagSizer.AddGrowableCol(1)
        
        self.AddUnits(parent = panel, dialogDict = self.scalebarDict)
        self.AddPosition(parent = panel, dialogDict = self.scalebarDict)
        
        if self.scalebarDict['rect']: # set position, ref point is center and not left top corner
            
            x = self.unitConv.convert(value = self.scalebarDict['where'][0] - self.scalebarDict['rect'].Get()[2]/2,
                                                    fromUnit = 'inch', toUnit = self.scalebarDict['unit'])
            y = self.unitConv.convert(value = self.scalebarDict['where'][1] - self.scalebarDict['rect'].Get()[3]/2,
                                                    fromUnit = 'inch', toUnit = self.scalebarDict['unit'])
            panel.position['xCtrl'].SetValue("{0:5.3f}".format(x))
            panel.position['yCtrl'].SetValue("{0:5.3f}".format(y))
        
        gridBagSizer.Add(panel.units['unitsLabel'], pos = (0,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(panel.units['unitsCtrl'], pos = (0,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(panel.position['xLabel'], pos = (1,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(panel.position['xCtrl'], pos = (1,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(panel.position['yLabel'], pos = (2,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(panel.position['yCtrl'], pos = (2,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(panel.position['comment'], pos = (3,0), span = (1,2), flag =wx.ALIGN_BOTTOM, border = 0)
        
        sizer.Add(gridBagSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        #
        # size
        #
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Size")))
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        gridBagSizer = wx.GridBagSizer (hgap = 5, vgap = 5)
        gridBagSizer.AddGrowableCol(1)
        
        lengthText = wx.StaticText(panel, id = wx.ID_ANY, label = _("Length:"))
        heightText = wx.StaticText(panel, id = wx.ID_ANY, label = _("Height:"))
        
        self.lengthTextCtrl = wx.TextCtrl(panel, id = wx.ID_ANY, validator = TCValidator('DIGIT_ONLY'))
        self.lengthTextCtrl.SetToolTipString(_("Scalebar length is given in map units"))
        
        self.heightTextCtrl = wx.TextCtrl(panel, id = wx.ID_ANY, validator = TCValidator('DIGIT_ONLY'))
        self.heightTextCtrl.SetToolTipString(_("Scalebar height is real height on paper"))
        
        choices = ['default'] + self.unitConv.getMapUnits()
        self.unitsLength = wx.Choice(panel, id = wx.ID_ANY, choices = choices)
        choices = self.unitConv.getPageUnits()
        self.unitsHeight = wx.Choice(panel, id = wx.ID_ANY, choices = choices)
        
        # set values
        ok = self.unitsLength.SetStringSelection(self.scalebarDict['unitsLength'])
        if not ok:
            if self.scalebarDict['unitsLength'] == 'auto':
                 self.unitsLength.SetSelection(0)
            elif self.scalebarDict['unitsLength'] == 'nautmiles':
                 self.unitsLength.SetStringSelection("nautical miles")                
        self.unitsHeight.SetStringSelection(self.scalebarDict['unitsHeight'])
        if self.scalebarDict['length']:
            self.lengthTextCtrl.SetValue(str(self.scalebarDict['length']))
        else: #estimate default
            reg = grass.region()
            w = int((reg['e'] - reg['w'])/4)
            w = round(w, -len(str(w)) + 2) #12345 -> 12000
            self.lengthTextCtrl.SetValue(str(w))
            
        h = self.unitConv.convert(value = self.scalebarDict['height'], fromUnit = 'inch',
                                                toUnit =  self.scalebarDict['unitsHeight']) 
        self.heightTextCtrl.SetValue(str(h))
        
        gridBagSizer.Add(lengthText, pos = (0,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.lengthTextCtrl, pos = (0, 1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.unitsLength, pos = (0, 2), flag = wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border = 0)
        gridBagSizer.Add(heightText, pos = (1,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.heightTextCtrl, pos = (1, 1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.unitsHeight, pos = (1, 2), flag = wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border = 0)

        
        sizer.Add(gridBagSizer, proportion = 1, flag = wx.EXPAND|wx.ALL, border = 5)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        #
        #style
        #
        box   = wx.StaticBox (parent = panel, id = wx.ID_ANY, label = " {0} ".format(_("Style")))
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        gridBagSizer = wx.GridBagSizer (hgap = 5, vgap = 5)
        
        
        sbTypeText = wx.StaticText(panel, id = wx.ID_ANY, label = _("Type:"))
        self.sbCombo = wx.combo.BitmapComboBox(panel, style = wx.CB_READONLY)
        # only temporary, images must be moved away
        self.sbCombo.Append(item = 'fancy', bitmap = wx.Bitmap("./images/scalebar-fancy.png"), clientData = 'f')
        self.sbCombo.Append(item = 'simple', bitmap = wx.Bitmap("./images/scalebar-simple.png"), clientData = 's')
        if self.scalebarDict['scalebar'] == 'f':
            self.sbCombo.SetSelection(0)
        elif self.scalebarDict['scalebar'] == 's':
            self.sbCombo.SetSelection(1)
            
        sbSegmentsText = wx.StaticText(panel, id = wx.ID_ANY, label = _("Number of segments:"))
        self.sbSegmentsCtrl = wx.SpinCtrl(panel, id = wx.ID_ANY, min = 1, max = 30, initial = 4)
        self.sbSegmentsCtrl.SetValue(self.scalebarDict['segment'])
        
        sbLabelsText1 = wx.StaticText(panel, id = wx.ID_ANY, label = _("Label every "))
        sbLabelsText2 = wx.StaticText(panel, id = wx.ID_ANY, label = _("segments"))
        self.sbLabelsCtrl = wx.SpinCtrl(panel, id = wx.ID_ANY, min = 1, max = 30, initial = 1)
        self.sbLabelsCtrl.SetValue(self.scalebarDict['numbers'])
        
        #font
        fontsizeText = wx.StaticText(panel, id = wx.ID_ANY, label = _("Font size:"))
        self.fontsizeCtrl = wx.SpinCtrl(panel, id = wx.ID_ANY, min = 4, max = 30, initial = 10)
        self.fontsizeCtrl.SetValue(self.scalebarDict['fontsize'])
        
        self.backgroundCheck = wx.CheckBox(panel, id = wx.ID_ANY, label = _("transparent text background"))
        self.backgroundCheck.SetValue(False if self.scalebarDict['background'] == 'y' else True)

            
        gridBagSizer.Add(sbTypeText, pos = (0,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.sbCombo, pos = (0,1), span = (1, 2), flag = wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border = 0)
        gridBagSizer.Add(sbSegmentsText, pos = (1,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.sbSegmentsCtrl, pos = (1,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(sbLabelsText1, pos = (2,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.sbLabelsCtrl, pos = (2,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(sbLabelsText2, pos = (2,2), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(fontsizeText, pos = (3,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.fontsizeCtrl, pos = (3,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        gridBagSizer.Add(self.backgroundCheck, pos = (4, 0), span = (1,3), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        
        sizer.Add(gridBagSizer, proportion = 1, flag = wx.ALIGN_CENTER_VERTICAL, border = 5)
        border.Add(item = sizer, proportion = 0, flag = wx.ALL | wx.EXPAND, border = 5)
        
        panel.SetSizer(border)
        
        return panel

                           
                    
    def update(self):
        """!Save information from dialog"""

        #units
        currUnit = self.panel.units['unitsCtrl'].GetStringSelection()
        self.scalebarDict['unit'] = currUnit
        # position
        x = self.panel.position['xCtrl'].GetValue() if self.panel.position['xCtrl'].GetValue() else self.scalebarDict['where'][0]
        y = self.panel.position['yCtrl'].GetValue() if self.panel.position['yCtrl'].GetValue() else self.scalebarDict['where'][1]
        x = self.unitConv.convert(value = float(self.panel.position['xCtrl'].GetValue()), fromUnit = currUnit, toUnit = 'inch')
        y = self.unitConv.convert(value = float(self.panel.position['yCtrl'].GetValue()), fromUnit = currUnit, toUnit = 'inch')
        
        
        # size
        
        # height
        self.scalebarDict['unitsHeight'] = self.unitsHeight.GetStringSelection()
        try:
            height = float(self.heightTextCtrl.GetValue())  
            height = self.unitConv.convert(value = height, fromUnit = self.scalebarDict['unitsHeight'], toUnit = 'inch') 
        except ValueError, SyntaxError:
            height = 0.1 #default in inch
        self.scalebarDict['height'] = height    
        
        #length
        selected = self.unitsLength.GetStringSelection()
        if selected == 'default':
            selected = 'auto'
        elif selected == 'nautical miles':
            selected = 'nautmiles'
        self.scalebarDict['unitsLength'] = selected
        try:
            length = float(self.lengthTextCtrl.GetValue())
        except ValueError, SyntaxError:
            wx.MessageBox(message = _("Length of scale bar is not defined"),
                                    caption = _('Invalid input'), style = wx.OK|wx.ICON_ERROR)
            return False
        self.scalebarDict['length'] = length
        
        if self.scalebarDict['unitsLength'] != 'auto':
            length = self.unitConv.convert(value = length, fromUnit = self.unitsLength.GetStringSelection(), toUnit = 'inch')
        else:
            length = self.unitConv.convert(value = length, fromUnit = self.mapUnit, toUnit = 'inch')
        # estimation of size
        mapId = find_key(dic = self.itemType, val = 'map')
        if not mapId:
            mapId = find_key(dic = self.itemType, val = 'initMap')
        length *= self.dialogDict[mapId]['scale']
        length *= 1.1 #for numbers on the edge
        fontsize = 10
        height = height + 2 * self.unitConv.convert(value = fontsize, fromUnit = 'point', toUnit = 'inch') 
        self.scalebarDict['rect'] = wx.Rect2D(x, y, length, height)
          
        
        self.scalebarDict['where'] = self.scalebarDict['rect'].GetCentre()  

        #style
        self.scalebarDict['scalebar'] = self.sbCombo.GetClientData(self.sbCombo.GetSelection())
        self.scalebarDict['segment'] = self.sbSegmentsCtrl.GetValue()
        self.scalebarDict['numbers'] = self.sbLabelsCtrl.GetValue()
        self.scalebarDict['fontsize'] = self.fontsizeCtrl.GetValue()
        self.scalebarDict['background'] = 'n' if self.backgroundCheck.GetValue() else 'y'

        
        

        
        
        self.dialogDict[self.id] = self.scalebarDict
        self.itemType[self.id] = 'scalebar'
        if self.id not in self.parent.objectId:
            self.parent.objectId.append(self.id)
            
        return True
    
      
class TextDialog(PsmapDialog):
    def __init__(self, parent, id, settings, itemType):
        PsmapDialog.__init__(self, parent = parent, id = id, title = "Text settings", settings = settings, itemType = itemType)
        
        self.new = True
        if self.id is not None:
            self.textDict = self.dialogDict[id] 
            self.new = False
        else:
            self.textDict = dict(self.parent.GetDefault('text'))
            self.id = wx.NewId()        
        
        self.mapId = find_key(dic = self.itemType, val = 'map')
        if self.mapId is None:
            self.mapId = find_key(dic = self.itemType, val = 'initMap')

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
        
        flexGridSizer.Add(panel.font['fontLabel'], proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        flexGridSizer.Add(panel.font['fontCtrl'], proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        flexGridSizer.Add(panel.font['colorLabel'], proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)        
        flexGridSizer.Add(panel.font['colorCtrl'], proportion = 0, flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        
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
        self.effect['backgroundColor'].SetColour(convertRGB(self.textDict['background']) 
                                            if self.textDict['background'] != 'none' else 'white')
        self.effect['highlightCtrl'].SetValue(True if self.textDict['hcolor'] != 'none' else False)
        self.effect['highlightColor'].SetColour(convertRGB(self.textDict['hcolor']) 
                                            if self.textDict['hcolor'] != 'none' else 'grey')
        self.effect['highlightWidth'].SetValue(float(self.textDict['hwidth']))
        self.effect['borderCtrl'].SetValue(True if self.textDict['border'] != 'none' else False)
        self.effect['borderColor'].SetColour(convertRGB(self.textDict['border']) 
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
        panel.position['comment'].SetLabel(_("Position from the top left\nedge of the paper"))
        self.AddUnits(parent = panel, dialogDict = self.textDict)
        self.gridBagSizerP.Add(panel.units['unitsLabel'], pos = (0,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        self.gridBagSizerP.Add(panel.units['unitsCtrl'], pos = (0,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        self.gridBagSizerP.Add(panel.position['xLabel'], pos = (1,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        self.gridBagSizerP.Add(panel.position['xCtrl'], pos = (1,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        self.gridBagSizerP.Add(panel.position['yLabel'], pos = (2,0), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        self.gridBagSizerP.Add(panel.position['yCtrl'], pos = (2,1), flag = wx.ALIGN_CENTER_VERTICAL, border = 0)
        self.gridBagSizerP.Add(panel.position['comment'], pos = (3,0), span = (1,2), flag = wx.ALIGN_BOTTOM, border = 0)
        
        
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
        font = self.textPanel.font['fontCtrl'].GetSelectedFont()
        self.textDict['font'] = font.GetFaceName()
        self.textDict['fontsize'] = font.GetPointSize()
        self.textDict['color'] = self.textPanel.font['colorCtrl'].GetColour().GetAsString(flags=wx.C2S_NAME)
        #effects
        self.textDict['background'] = (convertRGB(self.effect['backgroundColor'].GetColour())
                                        if self.effect['backgroundCtrl'].GetValue() else 'none') 
        self.textDict['border'] = (convertRGB(self.effect['borderColor'].GetColour())
                                        if self.effect['borderCtrl'].GetValue() else 'none')
        self.textDict['width'] = self.effect['borderWidth'].GetValue()
        self.textDict['hcolor'] = (convertRGB(self.effect['highlightColor'].GetColour())
                                        if self.effect['highlightCtrl'].GetValue() else 'none')
        self.textDict['hwidth'] = self.effect['highlightWidth'].GetValue()
        
        #offset
        self.textDict['xoffset'] = self.xoffCtrl.GetValue()
        self.textDict['yoffset'] = self.yoffCtrl.GetValue()
        #position
        if self.paperPositionCtrl.GetValue():
            self.textDict['XY'] = True
            currUnit = self.positionPanel.units['unitsCtrl'].GetStringSelection()
            self.textDict['unit'] = currUnit
            x = self.positionPanel.position['xCtrl'].GetValue() if self.positionPanel.position['xCtrl'].GetValue() else self.textDict['where'][0]
            y = self.positionPanel.position['yCtrl'].GetValue() if self.positionPanel.position['yCtrl'].GetValue() else self.textDict['where'][1]
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
                
        
        if self.new:
            self.dialogDict[self.id] = self.textDict
            self.itemType[self.id] = 'text'
            self.parent.objectId.append(self.id)
            self.new = False

        return True
    
    
    
def find_key(dic, val, multiple = False):
    """!Return the key of dictionary given the value"""
    result = [k for k, v in dic.iteritems() if v == val]
    if len(result) == 0 and not multiple:
        return None
    return sorted(result) if multiple else result[0]

def convertRGB(rgb):
    """!Converts wx.Colour(255,255,255,255) and string '255:255:255',
            depends on input"""    
    if type(rgb) == wx.Colour:
        return str(rgb.Red()) + ':' + str(rgb.Green()) + ':' + str(rgb.Blue())
    elif type(rgb) == str:
        return wx.Colour(*map(int, rgb.split(':')))
        
        
def PaperMapCoordinates(self, mapId, x, y, paperToMap = True):
    """!Converts paper (inch) coordinates -> map coordinates"""
    unitConv = UnitConversion(self)
    currRegionDict = grass.region()
    cornerEasting, cornerNorthing = currRegionDict['w'], currRegionDict['n']
    xMap = self.dialogDict[mapId]['rect'][0]
    yMap = self.dialogDict[mapId]['rect'][1]
    widthMap = self.dialogDict[mapId]['rect'][2] * 0.0254 # to meter
    heightMap = self.dialogDict[mapId]['rect'][3] * 0.0254
    xScale = widthMap / abs(currRegionDict['w'] - currRegionDict['e'])
    yScale = heightMap / abs(currRegionDict['n'] - currRegionDict['s'])
    currScale = (xScale + yScale) / 2

    
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
    
    
def AutoAdjust(self, scaleType,  rect, map = None, mapType = None, region = None):
    """!Computes map scale and map frame rectangle to fit region (scale is not fixed)"""
    currRegionDict = {}
    if scaleType == 0 and map:# automatic, region from raster or vector
        res = ''
        if mapType == 'raster': 
            res = grass.read_command("g.region", flags = 'gu', rast = map)
        elif mapType == 'vector':
            res = grass.read_command("g.region", flags = 'gu', vect = map)
        currRegionDict = grass.parse_key_val(res, val_type = float)
    elif scaleType == 1 and region: # saved region
        res = grass.read_command("g.region", flags = 'gu', region = region)
        currRegionDict = grass.parse_key_val(res, val_type = float)
    else:
        return None, None
    
    if not currRegionDict:
        return None, None
    rX = rect.x
    rY = rect.y
    rW = rect.width
    rH = rect.height
    if not hasattr(self, 'unitConv'):
        self.unitConv = UnitConversion(self)
    toM = 1
    if projInfo()['proj'] != 'xy':
        toM = float(projInfo()['meters'])

    mW = self.unitConv.convert(value = (currRegionDict['e'] - currRegionDict['w']) * toM, fromUnit = 'meter', toUnit = 'inch')
    mH = self.unitConv.convert(value = (currRegionDict['n'] - currRegionDict['s']) * toM, fromUnit = 'meter', toUnit = 'inch')
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

    return scale, wx.Rect2D(x, y, rWNew, rHNew) #inch

def ComputeSetRegion(self, mapDict):
    """!Computes and sets region from current scale, map center coordinates and map rectangle"""

    if mapDict['scaleType'] == 2: # fixed scale
        scale = mapDict['scale']
            
        if not hasattr(self, 'unitConv'):
            self.unitConv = UnitConversion(self)
        
        fromM = 1
        if projInfo()['proj'] != 'xy':
            fromM = float(projInfo()['meters'])
        rectHalfInch = ( mapDict['rect'].width/2, mapDict['rect'].height/2)
        rectHalfMeter = ( self.unitConv.convert(value = rectHalfInch[0], fromUnit = 'inch', toUnit = 'meter')/ fromM /scale,
                                self.unitConv.convert(value = rectHalfInch[1], fromUnit = 'inch', toUnit = 'meter')/ fromM /scale) 
        
        centerE = mapDict['center'][0]
        centerN = mapDict['center'][1]
        
        rasterId = find_key(dic = self.itemType, val = 'raster', multiple = False)
        if rasterId:
            RunCommand('g.region', n = ceil(centerN + rectHalfMeter[1]),
                           s = floor(centerN - rectHalfMeter[1]),
                           e = ceil(centerE + rectHalfMeter[0]),
                           w = floor(centerE - rectHalfMeter[0]),
                           rast = self.dialogDict[rasterId]['raster'])
        else:
            RunCommand('g.region', n = ceil(centerN + rectHalfMeter[1]),
                           s = floor(centerN - rectHalfMeter[1]),
                           e = ceil(centerE + rectHalfMeter[0]),
                           w = floor(centerE - rectHalfMeter[0]))
                    
def projInfo():
    """!Return region projection and map units information,
    taken from render.py"""
    
    projinfo = dict()
    
    ret = RunCommand('g.proj', read = True, flags = 'p')
    
    if not ret:
        return projinfo
    
    for line in ret.splitlines():
        if ':' in line:
            key, val = line.split(':')
            projinfo[key.strip()] = val.strip()
        elif "XY location (unprojected)" in line:
            projinfo['proj'] = 'xy'
            projinfo['units'] = ''
            break
    
    return projinfo
