import os

# demo receorse filesystem

# create 2 flat dictionaries for
# forward and reverse search
# path->handle and handle->path

# global handle incremented
next_handle=0

path2handle={}
handle2path={}

DIR=const(16384)
#FILE=const(32768)

# path: full path string
# recurse: number of subdirectorys to recurse into
def ls(path,recurse):
  global next_handle
  path2handle[path]=next_handle
  handle2path[next_handle]=path
  next_handle+=1

  dir=os.ilistdir(path)
  for obj in dir:
    if path=="/":
      fullpath="/"+obj[0]
    else:
      fullpath=path+"/"+obj[0]
    if obj[1]==DIR:
      print(path,"DIR:",obj)
      if recurse>0:
        ls(fullpath,recurse-1)
    else: # FILE
      print(path,"FILE:",obj)
      path2handle[fullpath]=next_handle
      handle2path[next_handle]=fullpath
      next_handle+=1

ls("/",3)
print(handle2path)
print(path2handle)
    