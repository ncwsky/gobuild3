#!/usr/bin/env python
# coding: utf-8

import argparse
import hashlib
import json
import os
import re
import sys
import time

import sh

pathjoin = os.path.join

packer_path = pathjoin(os.path.dirname(os.path.abspath(__file__)), 'packer')
packer = sh.Command(packer_path)
reponame = ''

outjson = {}
OUTDIR = '/output'
BASHPS1 = '\033[95mbash$ \033[0m'

osxenv = '/osxcross/target/bin/osxcross-env'
CC = dict(linux_arm='arm-linux-gnueabi-gcc',
        windows_amd64='x86_64-w64-mingw32-gcc',
        windows_386='i686-w64-mingw32-gcc',
        darwin_amd64='o64-clang',
        darwin_386='o32-clang')

def binname(reponame):
    basename = os.path.basename(reponame)

def hashsum(method, filepath):
    ''' method = md5 or sha1 '''
    with open(filepath, 'rb') as f:
        obj = eval('hashlib.%s()' % method)
        obj.update(f.read())
        return obj.hexdigest()

def build(goos, goarch, env={}):
    osarch = goos+'_'+goarch

    envcopy = os.environ.copy()
    envcopy.update(env)
    env = envcopy
    env.update({'GOOS': goos, 'GOARCH': goarch, 'CGO_ENABLED':'1', 'CC': CC.get(osarch, '')})

    logname = 'build-%s-%s.log' %(goos, goarch)
    outfd = open(pathjoin(OUTDIR, logname), 'w')

    basename = os.path.basename(reponame)
    ext = 'zip' if goos != 'linux' else 'tar.gz'
    outname = '%s-%s-%s.%s' %(basename, goos, goarch, ext)
    outpath = pathjoin(OUTDIR, outname)

    print BASHPS1+'CGO_ENABLED=1 GOOS=%s GOARCH=%s CC=%s'%(goos, goarch, CC.get(osarch,'')), 'packer --rm -o %s' % outpath
    ret = packer('--rm', '-o', outpath, _err_to_out=True, _out=outfd, _tee=True, _ok_code=range(255), _env=env)
    #ret = sh.go.build(_env=env, _err_to_out=True, _out=outfd, _tee=True, _ok_code=range(255))
    if ret.exit_code != 0:
        print 'Bulid error on(%s/%s), exit_code(%d)' %(goos, goarch, ret.exit_code)
        print '------------\n\033[93m'+str(ret)+'\033[0m' # warning color
        return False

    info = outjson['files'][osarch]={}
    info['size'] = os.path.getsize(outpath)
    info['md5'] = hashsum('md5', outpath)
    info['sha'] = hashsum('sha1', outpath)
    info['outname'] = outname
    info['logname'] = logname

    return True

def fetch(reponame, tag):
    print BASHPS1+'gopm --strict get -v -d %s@%s' %(reponame, tag)
    sh.gopm('--strict', 'get', '-v', '-d', reponame+'@'+tag, _err_to_out=True, _out=sys.stdout)
    print BASHPS1+'go get -v -d %s' %(reponame)
    sh.go.get('-v', '-d', reponame, _err_to_out=True, _out=sys.stdout)

def main():
    parser = argparse.ArgumentParser(description='cross compile build for golang')
    parser.add_argument('--repo', dest='repo', required=True)
    parser.add_argument('--tag', dest='tag', default='branch:master')
    args = parser.parse_args()

    global reponame
    reponame = args.repo
    tag = args.tag

    outjson['repo'] = reponame
    outjson['tag'] = tag
    outjson['created'] = int(time.time())
    outjson['version'] = '%s%s' %(sh.go.version(), sh.gopm('-v'))
    outjson['files'] = {}

    print 'Fetching', reponame
    fetch(reponame, tag)
    rdir = pathjoin(os.getenv('GOPATH'), 'src', args.repo)
    os.chdir(rdir) # change directory

    outjson['gobuildrc'] = open('.gobuild.yml').read() if os.path.exists('.gobuild.yml') else '# nothing'

    os_archs = [('linux','amd64'), ('linux','386'), ('linux','arm'),
            ('windows','amd64'), ('windows','386'),
            ('darwin','amd64'), ('darwin','386')]

    for goos, arch in os_archs:
        print '\033[92mBuilding for %s,%s\033[0m' %(goos, arch) # green color
        env = {}
        if goos == 'darwin':
            exportenv = str(sh.bash('-c', osxenv))
            for (key, value) in re.findall(r'export\s+([\w_]+)=([^\s]+)', exportenv):
                env[key] = value
        build(goos, arch, env=env)

    outjson['time_used'] = int(time.time())-outjson['created']
    print 'Saving state to out.json'
    print '------------ out.json -------------'
    with open(pathjoin(OUTDIR, 'out.json'), 'w') as f:
        json.dump(outjson, f)
    print json.dumps(outjson, indent=4)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e)
        sys.exit(1)
