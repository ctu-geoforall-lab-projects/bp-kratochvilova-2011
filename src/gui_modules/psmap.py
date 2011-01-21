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
        self.zoomIn = wx.NewId()
        self.zoomOut = wx.NewId()
        self.zoomAll = wx.NewId()
        
        # tool, label, bitmap, kind, shortHelp, longHelp, handler
        return (
            (self.pagesetup, 'page setup', Icons['settings'].GetBitmap(),
             wx.ITEM_NORMAL, "Page setup", "Specify paper size, margins and orientation",
             self.parent.OnPageSetup),
            (self.zoomAll, 'full extent', Icons['zoom_extent'].GetBitmap(),
             wx.ITEM_NORMAL, "Full extent", "Zoom to full extent",
             self.parent.OnZoomAll),
            (self.zoomIn, 'zoom in', Icons['zoom_in'].GetBitmap(),
             wx.ITEM_NORMAL, "Zoom in", "Zoom in to specified region",
             self.parent.OnZoomIn),
            (self.zoomOut, 'zoom out', Icons['zoom_out'].GetBitmap(),
             wx.ITEM_NORMAL, "Zoom out", "Zoom out",
             self.parent.OnZoomOut),
            (self.quit, 'quit', Icons['quit'].GetBitmap(),
             wx.ITEM_NORMAL, Icons['quit'].GetLabel(), Icons['quit'].GetDesc(),
             self.parent.OnCloseWindow)
            )
class PageSetupDialog(wx.Dialog):
    def __init__(self, parent, pageSetupDict):
        wx.Dialog.__init__(self, parent = parent, id = wx.ID_ANY, title = "Page setup", size = wx.DefaultSize, style = wx.DEFAULT_DIALOG_STYLE)
        
        self.cat = ['Units', 'Format', 'Orientation', 'Width', 'Height', 'Left', 'Right', 'Top', 'Bottom']
        paperString = RunCommand('ps.map', flags = 'p', read = True)
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
        try:
            self._update()
        except ValueError:
                dlg = wx.MessageDialog(None,_("Literal is not allowed!"), _('Invalid input'), style=wx.OK|wx.ICON_ERROR)
                dlg.Destroy()
        else:
            event.Skip()
        
    def doLayout(self):
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
        
        sizeList = list()
        for line in paperStr.strip().split('\n'):
            d = dict(zip([self.cat[1]]+ self.cat[3:],line.split()))
            sizeList.append(d)
        d = {}.fromkeys([self.cat[1]]+ self.cat[3:], 100)
        d.update(Format = 'custom')
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
        #menubar
        self.menubar = menu.Menu(parent = self, data = PsMapData())
        self.SetMenuBar(self.menubar)
        #toolbar
        self.toolbar = PsMapToolbar(parent = self)
        self.SetToolBar(self.toolbar)
        #satusbar
        self.statusbar = self.CreateStatusBar(number = 1)
        

            
        self.SetDefault()
        self.canvas = PsMapBufferedWindow(parent = self)
        
        
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        
        self._layout()
        self.SetMinSize(wx.Size(700, 600))
        
        # default settings 
    def SetDefault(self, **kwargs):
        self.pageSetupDict = dict(zip(PageSetupDialog(self, None).cat,
                                ['inch','a4','Portrait',8.268, 11.693, 0.5, 0.5, 1, 1]))
            
    def _layout(self):
        """!Do layout
        """
        pass
    
    def OnPageSetup(self, event = None):
        """!Specify paper size, margins and orientation"""
        dlg = PageSetupDialog(self, self.pageSetupDict) 
        dlg.CenterOnScreen()
        val = dlg.ShowModal()
        if val == wx.ID_OK:
            self.pageSetupDict=dlg.getInfo()
            self.canvas.SetPage()
        dlg.Destroy()
        
    def OnZoomIn(self, event):
        self.canvas.mouse["use"] = "zoomin"
        
    def OnZoomOut(self, event):
        self.canvas.mouse["use"] = "zoomout"
        
    def OnZoomAll(self, event):
        self.canvas.mouse["use"] = "zoomall"
        self.canvas.ZoomAll()
        
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
    
        self.FitInside()
        self.SetScrollRate(20,20)
      
        # store an off screen empty bitmap for saving to file
        self._buffer = None
        # indicates whether or not a resize event has taken place
        self.resize = False 
        
        # mouse attributes -- position on the screen, begin and end of
        # dragging, and type of drawing
        self.mouse = {
            'begin': [0, 0], # screen coordinates
            'end'  : [0, 0],
            'use'  : "pointer",
            }
        # pen and brush
        self.pen = {
            'paper': wx.Pen("BLACK", 1),
            'object': wx.Pen("RED", 2)
            }
        self.brush = {
            'paper': wx.WHITE_BRUSH,
            'object': wx.GREEN_BRUSH
            }
        # define PseudoDC
        self.pdcObj = wx.PseudoDC()
        self.pdcPaper = wx.PseudoDC()
        self.pdcTmp = wx.PseudoDC()
        
        self.SetClientSize((700,510))#?
        self._buffer = wx.EmptyBitmap(*self.GetClientSize())
        
        self.idPaper = None
        self.idVirtualPaper = None # it's used to set some free space around paper
        self.objIds = []
        self.objRectDic = {}
        self.idBoxTmp = 1000
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
        
        if self.idPaper:
            self.pdcPaper.RemoveId(self.idPaper)
        if self.idVirtualPaper:
            self.pdcPaper.RemoveId(self.idVirtualPaper)

        self.idPaper = wx.NewId()
        self.idVirtualPaper = wx.NewId()
        
        self.SetPage()
        

    def PageRect(self, pageDict, inflate = 0):
        """! Returnes offset and scaled page """
        cW, cH = self.GetClientSize()
        pW, pH = pageDict['Width']*72 + inflate, pageDict['Height']*72 + inflate
        if self.currScale is None:
            self.currScale = min(cW/pW, cH/pH)
        pW = pW * self.currScale
        pH = pH * self.currScale
        x = cW/2 - pW/2
        y = cH/2 - pH/2
        return wx.Rect(x, y, pW, pH)# pixel
        
    def SetPage(self):
        """!Sets and changes page, redraws paper"""
        vW, vH = self.GetVirtualSize()
        cW, cH = self.GetClientSize()
        virtualPaper = self.PageRect(pageDict = self.parent.pageSetupDict, inflate = 30)
        newPaper = self.PageRect(pageDict = self.parent.pageSetupDict, inflate = 0)
        pW, pH = virtualPaper.GetWidth(), virtualPaper.GetHeight()
        sc = max(float(pW)/vW, float(pH)/vH)
        vWNew = vW * sc
        vHNew = vH * sc
        self.SetVirtualSize((vWNew, vHNew))
        virtualPaper.OffsetXY((vWNew - cW)/2, (vHNew - cH)/2)
        newPaper.OffsetXY((vWNew - cW)/2, (vHNew - cH)/2)

        self.pdcPaper.SetIdBounds(self.idVirtualPaper, virtualPaper)
        
        self.Draw(pen = self.pen['paper'], brush = self.brush['paper'], pdc = self.pdcPaper,
                    pdctype = 'rect', drawid = self.idPaper, bb = newPaper)
        
        # move objects when they are out of virtual size            
        for objId in self.objIds:
            rect = self.pdcObj.GetIdBounds(objId)
            if not wx.Rect(0,0,*self.GetVirtualSize()).ContainsRect(rect):
                x, y = rect.GetBottomRight().x - vWNew, rect.GetBottomRight().y - vHNew
                rect.OffsetXY(-x, -y)
                self.Draw(pen = self.pen['object'], brush = self.brush['object'], pdc = self.pdcObj,
                            pdctype = 'rect', drawid = objId, bb = rect)


            
    def DrawObj(self, pdc):
        id = wx.NewId()
        testRect = wx.Rect(0,0,100,100)
        self.objRectDic[id] = testRect
        rect = self.ScaleRect(testRect, self.currScale)
        rect.OffsetXY(200,300)
        self.Draw(pen = self.pen['object'], brush = self.brush['object'], pdc = self.pdcObj,
                    pdctype = 'rect', drawid = id, bb = rect)
        self.objIds.append(id)

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
        xv, yv = self.GetViewStart()
        dx, dy = self.GetScrollPixelsPerUnit()
        x, y   = (xv * dx, yv * dy)
        rgn = self.GetUpdateRegion()
        rgn.Offset(x,y)
        
        self.pdcObj.DrawToDCClipped(dc, rgn.GetBox())
        self.pdcTmp.DrawToDCClipped(dc, rgn.GetBox())
    
    def OnMouse(self, event):
        if event.LeftDown():
            if self.mouse['use'] in ('zoomin', 'zoomout'):
                self.mouse['begin'] = self.CalcUnscrolledPosition(event.GetPosition())
                self.oldR = wx.Rect()
        elif event.Dragging():
            if self.mouse['use'] in ('zoomin', 'zoomout'):
                self.pdcTmp.BeginDrawing()
                self.pdcTmp.RemoveId(self.idBoxTmp)
                self.pdcTmp.SetId(self.idBoxTmp)
            
                self.pdcTmp.SetPen(wx.Pen('BLACK', 1))
                self.pdcTmp.SetBrush(wx.TRANSPARENT_BRUSH)

                #draw
                self.mouse['end'] = self.CalcUnscrolledPosition(event.GetPosition())
                r = wx.Rect(self.mouse['begin'][0], self.mouse['begin'][1],
                            self.mouse['end'][0]-self.mouse['begin'][0], self.mouse['end'][1]-self.mouse['begin'][1])
                r = self.modifyRectangle(r)
                self.pdcTmp.DrawRectangleRect(r)
                self.pdcTmp.SetIdBounds(self.idBoxTmp,r)
                #refresh
                r.Inflate(2,2)
                self.RefreshRect(self.oldR)
                xx,yy = self.CalcScrolledPosition(r.GetX(),r.GetY())
                r.SetX(xx)
                r.SetY(yy)
                self.oldR = r
                
                self.pdcTmp.EndDrawing()
        elif event.LeftUp():
            if self.mouse['use'] in ('zoomin','zoomout'):
                zoomR = self.pdcTmp.GetIdBounds(self.idBoxTmp)
                self.pdcTmp.RemoveId(self.idBoxTmp)
                self.Refresh()
                self.Zoom(zoomR)


        event.Skip()
            
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
                    x,y = self.CalcScrolledPosition(rect.GetX()-(rW-(cW/cH)*rH)/2, rect.GetY())
                    xView, yView = self.CalcUnscrolledPosition(-x, -y)
            else:
                xView = rect.GetX() - (rH*(cW/cH) - rW)/2
                yView = rect.GetY()
                if self.mouse['use'] == 'zoomout':
                    x,y = self.CalcScrolledPosition(rect.GetX(), rect.GetY() -(rH-(cH/cW)*rW)/2)
                    xView, yView = self.CalcUnscrolledPosition(-x, -y)
        return zoomFactor, (xView, yView)
               
                
    def Zoom(self, zoomR):
        """! Zoom to specified region, scroll view, redraw"""
        zoomFactor, view = self.ComputeZoom(zoomR)
        self.currScale = self.currScale*zoomFactor
        currSize = self.GetVirtualSize()
        currSize.Scale(zoomFactor, zoomFactor)
        # zoomin limit
        if currSize.GetWidth() > 10000:
            return
        self.SetVirtualSize(currSize)
        pPU = self.GetScrollPixelsPerUnit()
        self.Scroll(view[0]*zoomFactor/pPU[0], view[1]*zoomFactor/pPU[1])
        
        # redraw paper
        pRect = self.pdcPaper.GetIdBounds(self.idPaper)
        pRect = self.ScaleRect(rect = pRect, scale = zoomFactor)
        if pRect.GetWidth() < 50:# zoom out limit
            return 
        self.Draw(pen = self.pen['paper'], brush = self.brush['paper'], pdc = self.pdcPaper,
                    drawid = self.idPaper, pdctype = 'rect', bb = pRect)
        
        #redraw objects
        for objId in self.objIds:
            oRect = self.pdcObj.GetIdBounds(objId)
            oRect = self.ScaleRect(rect = oRect, scale = zoomFactor)
            self.Draw(pen = self.pen['object'], brush = self.brush['object'], pdc = self.pdcObj,
                        drawid = objId, pdctype = 'rect', bb = oRect)
            
        width, height = self.GetClientSize()
        self._buffer = wx.EmptyBitmap(width, height)
        
    def ZoomAll(self):
        """! Zoom to full extent"""
        for i in range(2):  # very dummy solution! in some cases it's necessary
            zoomP = self.pdcPaper.GetIdBounds(self.idVirtualPaper)
            self.Zoom(zoomP)
            self.SetVirtualSize(self.GetClientSize())
            width, height = self.GetClientSize()
            self._buffer = wx.EmptyBitmap(width, height)
            self.SetPage()
                    
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
