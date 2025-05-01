import os

# demo receorse filesystem

# create 2 flat dictionaries for
# forward and reverse search
# path->handle and handle->path

# global handle incremented
next_handle=0

path2handle={}
handle2path={}
dir2handles={}

DIR=const(16384)
#FILE=const(32768)

# path: full path string
# recurse: number of subdirectorys to recurse into
def ls(path,recurse):
  global next_handle
  try:
    dir=os.ilistdir(path)
  except:
    return
  # path -> handle and handle -> path
  if path in path2handle:
    current_dir=path2handle[path]
  else:
    current_dir=next_handle
    next_handle+=1
    path2handle[path]=current_dir
    handle2path[current_dir]=path
    if path=="/":
      print("root", current_dir)
  # id -> directory list
  if not current_dir in dir2handles:
    dir2handles[current_dir]={}
  for obj in dir:
    if path=="/":
      fullpath="/"+obj[0]
    else:
      fullpath=path+"/"+obj[0]
    if fullpath in path2handle:
      current_handle=path2handle[fullpath]
    else:
      current_handle=next_handle
      next_handle+=1
    dir2handles[current_dir][current_handle]=obj[0]
    if obj[1]==DIR:
      print(path,"DIR:",obj)
      if recurse>0:
        ls(fullpath,recurse-1)
    else: # obj[1]==FILE
      print(path,"FILE:",obj)
      if not fullpath in path2handle:
        path2handle[fullpath]=current_handle
        handle2path[current_handle]=fullpath

ls("/",3)
ls("/",3)
print(handle2path)
print(path2handle)
print(dir2handles)
