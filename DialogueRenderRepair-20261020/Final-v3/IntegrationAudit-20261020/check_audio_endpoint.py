"""Read Windows default playback endpoints; never reads voice credentials."""
import ctypes as c
import json
import uuid
import winreg

class Guid(c.Structure):
    _fields_=[('data',c.c_ubyte*16)]
    def __init__(self,value):super().__init__((c.c_ubyte*16).from_buffer_copy(uuid.UUID(value).bytes_le))

def call(obj,index,result,*argtypes):
    table=c.cast(obj,c.POINTER(c.POINTER(c.c_void_p))).contents
    return c.WINFUNCTYPE(result,c.c_void_p,*argtypes)(table[index])

def inspect():
    devices=[]
    base=r'SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render'
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,base) as key:
        for i in range(winreg.QueryInfoKey(key)[0]):
            ident=winreg.EnumKey(key,i)
            with winreg.OpenKey(key,ident) as device:
                state=winreg.QueryValueEx(device,'DeviceState')[0]
            with winreg.OpenKey(key,ident+r'\Properties') as props:
                try:name=winreg.QueryValueEx(props,'{a45c254e-df1c-4efd-8020-67d146a850e0},2')[0]+' ('+winreg.QueryValueEx(props,'{b3f8fa53-0004-438e-9003-51a46e139bfc},6')[0]+')'
                except OSError:name=''
            devices.append({'id':'{0.0.0.00000000}.'+ident,'name':name,'active':state==1})
    ole=c.OleDLL('ole32');ole.CoInitialize(None)
    clsid=Guid('bcde0395-e52f-467c-8e3d-c4579291692e');iid=Guid('a95664d2-9614-4f35-a746-de8db63617e6');obj=c.c_void_p()
    ole.CoCreateInstance(c.byref(clsid),None,1,c.byref(iid),c.byref(obj))
    defaults=[]
    for role in range(3):
        device=c.c_void_p()
        hr=call(obj,4,c.c_long,c.c_int,c.c_int,c.POINTER(c.c_void_p))(obj,0,role,c.byref(device))
        if hr<0:defaults.append({'role':role,'available':False});continue
        text=c.c_wchar_p()
        call(device,5,c.c_long,c.POINTER(c.c_wchar_p))(device,c.byref(text))
        ident=text.value
        defaults.append({'role':role,**next((d for d in devices if d['id'].lower()==ident.lower()),{'id':ident})})
        ole.CoTaskMemFree(text);call(device,2,c.c_ulong)(device)
    call(obj,2,c.c_ulong)(obj)
    return {'defaults':defaults,'activeDevices':[d for d in devices if d['active']],'picoDevices':[d for d in devices if 'pico' in d['name'].lower()]}

if __name__=='__main__':print(json.dumps(inspect(),ensure_ascii=False,indent=2))
