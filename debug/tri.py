import os

path2oh={}
oh2path={}
next_handle=0
# current list example
# { 1:('main.py',32768,0,123),
#   2:('lib',16384,0,0),
# }
cur_list={}
# object id of current parent directory
cur_parent=0

# VFS micrpython types ilistdir obj[1]
VFS_DIR=const(0x4000)
VFS_FILE=const(0x8000)

# list directory items
# update internal cache path -> object id
# cache obtained list of objects for later use
# path is directory with trailing slash
# recurse in number of subdirs to descend
def ls(path:str):
  global path2oh,oh2path,next_handle,cur_parent,cur_list
  try:
    dir=os.ilistdir(path)
  except:
    return
  if path in path2oh:
    cur_parent=path2oh[path]
  else:
    cur_parent=next_handle
    next_handle+=1
    path2oh[path]=cur_parent
    oh2path[cur_parent]=path    
  cur_list={}
  for obj in dir:
    if obj[1]==VFS_FILE:
      objname=obj[0]
    if obj[1]==VFS_DIR:
      objname=obj[0]+"/"
    fullpath=path+objname
    if fullpath in path2oh:
      oh=path2oh[fullpath]
    else:
      oh=next_handle
      next_handle+=1
      path2oh[fullpath]=oh
      oh2path[oh]=fullpath
    cur_list[oh]=obj
    print(oh,fullpath,obj)
