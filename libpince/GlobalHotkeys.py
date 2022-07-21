#!/usr/bin/python

class GlobalHotKey:
    def __init__(self, file, hotkey_list):
            self.file = file
            self.hotkey_list=hotkey_list
            self.last_keycode=0

    #return the string associated to the first keycode that match
    def match(self):
        while 1 :
            self.extract()
            for hotkey in self.hotkey_list:
                if self.last_keycode == hotkey[0]:
                    return hotkey[1] 

    #this function will extract the keycode from the last key pressed
    def extract(self):
        while 1 :
            x = self.file.read(24)
            key_type = (x[17]<<8)|x[16]
            key_code = (x[19]<<8)|x[18]
            key_value = (x[23]<<24)|(x[22]<<16)|(x[21]<<8)|x[20]
            if key_type == 1 and key_value == 1:
                self.last_keycode=key_code
                return 1

    
    #To do test if we don't know what keycode is our key
    def tests(self):
        while 1 :
            self.extract()
            print(self.last_keycode)
        

#you can find your event(number) with this command, just add the prefix /dev/input
#grep "keyboard" <( ls -l /dev/input/by-id/) | grep -Eo "[^.]+$"
#if there is multiple of them, just try them i haven't figured else.
filename="/dev/input/event3"


#it's based on a tuple (A, "B")
#Where A is a keycode (see below to how to get it).
#Where B is a string to identify it, i found it convenient to do so.
#To find what keycode is what key this link below usually helps, but it's based on an american qwerty keyboard
#https://github.com/torvalds/linux/blob/972a278fe60c361eb8f37619f562f092e8786d7c/include/uapi/linux/input-event-codes.h#L65  
#But you can use the tests method from the GlobalHotKey at least you're sure
hotkey_list=[(60, "F2"),(61, "F3")]
                          
try:
    with open(filename, "rb") as f:
        HK = GlobalHotKey(f,hotkey_list)
        while 1:
            matched_keybind=HK.match()
            print(matched_keybind)#just to see how it works

except OSError as e:
    print('open() failed', e)

    
