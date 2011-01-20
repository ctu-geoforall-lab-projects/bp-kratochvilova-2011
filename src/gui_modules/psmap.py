#!/usr/bin/python

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

sys.path.append(os.path.join(os.getenv('GISBASE'), 'etc', 'gui', 'wxpython', 'gui_modules'))
import globalvar
import menu
from   menudata   import MenuData, etcwxdir
from   toolbars   import AbstractToolbar
from   icon       import Icons
from   gcmd       import RunCommand
import wx


class UnitConversion():
    def __init__(self):
        self._unitEquivalence = {'inch':1,
                            'meter':0.0254,
                            'centimeter':2.54,
                            'milimeter':25.4}
    def getUnits(self):
        return self._unitEquivalence.keys()
    def convert(self, value, fromUnit=None, toUnit=None):
        return value/self._unitEquivalence[fromUnit]*self._unitEquivalence[toUnit]
        
    
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
        self.pagesetup = wx.NewId()
        
        # tool, label, bitmap, kind, shortHelp, longHelp, handler
        return (
            (self.pagesetup, 'page setup', Icons['settings'].GetBitmap(),
             wx.ITEM_NORMAL, "Page setup", "Specify paper size, margins and orientation",
             self.parent.OnPageSetup),
            (self.quit, 'quit', Icons['quit'].GetBitmap(),
             wx.ITEM_NORMAL, Icons['quit'].GetLabel(), Icons['quit'].GetDesc(),
             self.parent.OnCloseWindow)
            )
class PageSetupDialog(wx.Dialog):
    def __init__(self, parent, pageSetupDict):
        wx.Dialog.__init__(self, parent, -1, title="Page setup", size=wx.DefaultSize, style=wx.DEFAULT_DIALOG_STYLE)
        paperString = RunCommand('ps.map', flags='p', read=True)
        self.paperTable = self._toList(paperString) 
        self.units = UnitConversion()
        self.unitsList = self.units.getUnits()
        self.pageSetupDict = pageSetupDict

        self.doLayout()
        
        if self.pageSetupDict:
            for item in self.cat[:3]:
                self.getCtrl(item).SetSelection(self.getCtrl(item).FindString(self.pageSetupDict[item]))
            for item in self.cat[3:]:
                self.getCtrl(item).SetValue("{0:4.2f}".format(self.pageSetupDict[item]))
        else: #default
            self.pageSetupDict = dict()
            default = ['inch','a4','Portrait']
            for i, item in enumerate(self.cat[:3]):
                self.getCtrl(item).SetSelection(self.getCtrl(item).FindString(default[i]))
                self.pageSetupDict[item] = default[i]
            
            for item in self.cat[3:]:
                val = "{0:4.2f}".format(float(self.paperTable[0][item]))
                self.getCtrl(item).SetValue(val)
                self.pageSetupDict[item] = float(val)
       
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
            self.pageSetupDict[item] = float(self.getCtrl(item).GetValue())
            
    def OnOK(self, event):
        self._update()
        event.Skip()
        
    def doLayout(self):
        size = (110,-1)
        #sizers
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        pageBox = wx.StaticBox(self, id=wx.ID_ANY, label=" Page size ")
        pageSizer = wx.StaticBoxSizer(pageBox, wx.VERTICAL)
        marginBox = wx.StaticBox(self, id=wx.ID_ANY, label=" Margins ")
        marginSizer = wx.StaticBoxSizer(marginBox, wx.VERTICAL)
        horSizer = wx.BoxSizer(wx.HORIZONTAL) 
        #staticText + choice
        choices = [self.unitsList, [item['Format'] for item in self.paperTable], ['Portrait', 'Landscape']]
        propor = [0,1,1]
        border = [5,3,3]
        self.hBoxDict={}
        for i, item in enumerate(self.cat[:3]):
            hBox = wx.BoxSizer(wx.HORIZONTAL)
            stText = wx.StaticText(self, -1, label = item + ':')
            choice = wx.Choice(self, -1, choices = choices[i], size=size)
            hBox.Add(stText, proportion=propor[i], flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=border[i])
            hBox.Add(choice, proportion=0, flag=wx.ALL, border=border[i])
            if item == 'Units':
                hBox.Add(size,1) 
            self.hBoxDict[item] = hBox    

        #staticText + TextCtrl
        for item in self.cat[3:]:
            hBox = wx.BoxSizer(wx.HORIZONTAL)
            label = wx.StaticText(self, -1, label = item+':')
            textctrl = wx.TextCtrl(self, id=wx.ID_ANY, size=size, value='')
            hBox.Add(label, proportion=1, flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=3)
            hBox.Add(textctrl, proportion=0, flag=wx.ALIGN_CENTRE|wx.ALL, border=3)
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
    
    
        horSizer.Add(pageSizer, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM,10)
        horSizer.Add(marginSizer, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND,10)
        mainSizer.Add(horSizer, 0, 10)  
        mainSizer.Add(btnSizer, 0,wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.ALL, 10)      
        self.SetSizer(mainSizer)
        mainSizer.Fit(self)
    
    def OnChoice(self, event):
        currPaper = self.paperTable[self.getCtrl('Format').GetSelection()]
        currUnit = self.getCtrl('Units').GetString(self.getCtrl('Units').GetSelection())
        currOrient = self.getCtrl('Orientation').GetString(self.getCtrl('Orientation').GetSelection())
        newSize = dict()
        for item in self.cat[3:]:
            newSize[item] = self.units.convert(float(currPaper[item]), fromUnit='inch', toUnit=currUnit)

        enable = True
        if currPaper['Format'] != 'custom':
            if currOrient == 'Landscape':
                newSize['Width'], newSize['Height'] = newSize['Height'], newSize['Width']
                newSize['Left'], newSize['Right'], newSize['Top'], newSize['Bottom'] =\
                (newSize['Bottom'],newSize['Top'], newSize['Left'], newSize['Right'])
            for item in self.cat[3:]:
                self.getCtrl(item).ChangeValue("{0:4.2f}".format(newSize[item]))
            enable = False
        self.getCtrl('Width').Enable(enable)
        self.getCtrl('Height').Enable(enable)
        self.getCtrl('Orientation').Enable(not enable)


    def getCtrl(self, item):
         return self.hBoxDict[item].GetItem(1).GetWindow()
        
    def _toList(self, paperStr):
        self.cat = ['Units', 'Format', 'Orientation', 'Width', 'Height', 'Left', 'Right', 'Top', 'Bottom']
        sizeList = list()
        for line in paperStr.strip().split('\n'):
            d = dict(zip([self.cat[1]]+ self.cat[3:],line.split()))
            sizeList.append(d)
        d = {}.fromkeys([self.cat[1]]+ self.cat[3:], 100)
        d.update(Format='custom')
        sizeList.append(d)
        return sizeList
        
        
        
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
        self.pageSetupDict={}
        
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        
        self._layout()
        self.SetMinSize(wx.Size(700, 600))
        
    def _layout(self):
        """!Do layout
        """
        pass
    
    def OnPageSetup(self, event):
        """!Specify paper size, margins and orientation"""
        dlg = PageSetupDialog(self, self.pageSetupDict) 
        dlg.CenterOnScreen()
        val = dlg.ShowModal()
        if val == wx.ID_OK:
            self.pageSetupDict=dlg.getInfo()
        dlg.Destroy()
        
    def OnCloseWindow(self, event):
        """!Close window"""
        self.Destroy()

class PsMapBufferedWindow(wx.ScrolledWindow):
    """!A buffered window class.
    
    @param parent parent window
    @param kwargs other wx.Window parameters
    """
    def __init__(self, parent, id =  wx.ID_ANY,
                 style = wx.NO_FULL_REPAINT_ON_RESIZE,
                 **kwargs):
        wx.ScrolledWindow.__init__(self, parent, id = id, style = style, **kwargs)
        self.parent = parent
        self.maxWidth = 2000
        self.maxHeight = 2000
        self.SetBackgroundColour("WHITE")
        self.SetVirtualSize((self.maxWidth, self.maxHeight))
        self.SetScrollRate(20,20)
        
        # store an off screen empty bitmap for saving to file
        self._buffer = None
        # indicates whether or not a resize event has taken place
        self.resize = False 
        
        
        
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
        xv, yv = self.GetViewStart()
        dx, dy = self.GetScrollPixelsPerUnit()
        x, y   = (xv * dx, yv * dy)
        rgn = self.GetUpdateRegion()
        rgn.Offset(x,y)
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
