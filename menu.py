import pygame
import pygame_gui
class MenuItem:
    '''
    item of menu bar.
    for module private use.
    '''
    def __init__(self,label:str,rect,manager,parent,options:dict):
        self.label=label
        self.button=pygame_gui.elements.UIButton(rect,label,manager,parent)
        self.list=pygame_gui.elements.UISelectionList(pygame.Rect(rect[0],30,150,25*len(options.keys())),options.keys(),manager,parent_element=self.button)
        self.list.hide()
        self.options=options

class MenuBar:
    def __init__(self,width,manager):
        self.items=[]
        self.manager=manager
        self.ui=pygame_gui.elements.UIPanel((0,0,width,30),\
                anchors={'top':'top','left':'left','right':'right'},manager=manager)
        self.__list_hovered=None
    def add_item(self,label:str,content:dict):
        '''
        add a menu item with dropdown contents.
        one-time setting. cannot be modified again.
        strucure of content should be like this:
        {label:funtion,...}
        '''
        rect=pygame.Rect(len(self.items)*150,0,150,30)
        self.items.append(MenuItem(label,rect,self.manager,self.ui,content))
    def tackle_event(self,event:pygame.Event,time_delta):
        '''
        send event here in a pygame event loop to let the menu deal with events.
        '''
        if event.type==pygame_gui.UI_BUTTON_ON_HOVERED or event.type==pygame_gui.UI_BUTTON_PRESSED:
            #check menu bar
            #display the list of hovered button
            for i in self.items:
                i:MenuItem
                if event.ui_element==i.button:
                    if not self.__list_hovered is None and self.__list_hovered !=i.list:
                        self.__list_hovered.hide()
                    i.list.show()
        elif event.type==pygame.MOUSEMOTION:
            """ 
            here we check if we moved out of a list or into a list
            if out of a list, then we should hide it. if into, then record it 
            in __list_hovered. 
            """
            mx,my=pygame.mouse.get_pos()
            for i in self.items:
                i:MenuItem
                if i.list.visible and i.list.check_hover(time_delta,False):
                    if not self.__list_hovered is None and self.__list_hovered !=i.list:
                        self.__list_hovered.hide()
                    self.__list_hovered=i.list
                    if not i.list.visible:
                        i.list.show()
                    break
            else:
                if not self.__list_hovered is None:
                    #a list is shown, but not hovered
                    self.__list_hovered.hide()
                    self.__list_hovered=None
        elif event.type==pygame_gui.UI_SELECTION_LIST_NEW_SELECTION:
            #selected a menu item
            for i in self.items:
                i:MenuItem
                if i.list==event.ui_element:
                    #this is the list selected
                    #run the function
                    text=event.text
                    i.options[text]()
                    break
        elif event.type==pygame.VIDEORESIZE:
            self.ui.rect.width=event.w