__FILENAME__ = CoreXZ transform
import math,copy
def getABC(position1):
    if "X" not in position1:
        return position1
    position=copy.deepcopy(position1)
    xs,ys,zs=coord["X"],coord["Y"],coord["Z"]
    x,y,z,f=position["X"],position["Y"],position["Z"],position["F"]
    a1,b1,c1=xs-zs,ys,xs+zs
    a2,b2,c2=x-z,y,x+z
    virtual_d=math.sqrt((a1-a2)**2+(b1-b2)**2+(c1-c2)**2)
    d=math.sqrt((x-xs)**2+(y-ys)**2+(z-zs)**2)
    fnew=f
    if d!=0:
        fnew=f*virtual_d/d
    position['X']=a2
    position['Y']=b2
    position['Z']=c2
    position['F']=fnew
    return position

coord={"X":0,"Y":0,"Z":0, "E":0, "F":1200}

f=file(raw_input("Input File: "))
prefixes="MGXYZESF"
commands="MG"
f2=file(raw_input("Output File: "),"w")
f2.write("G92 X0 Y0 Z0 E0\n")
program=[]
move_count=0
for line in f:
    line=line.strip()
    chunks=line.split(";")[0].split(" ")
    stuff={}
    for chunk in chunks:
        if len(chunk)>1:
            stuff[chunk[0]]=chunk[1:]
            try:
                stuff[chunk[0]]=int(stuff[chunk[0]])
            except:
                try:
                    stuff[chunk[0]]=float(stuff[chunk[0]])
                except:
                    pass
        if "X" in stuff or "Y" in stuff or "Z" in stuff:
            move_count+=1
            for c in coord:
                if c not in stuff:
                    stuff[c]=coord[c]           
    program+=[stuff]
    for c in coord:
        if c in stuff:
            coord[c]=stuff[c]

for line in program:
    abcline=getABC(line)
    for letter in prefixes:
        if letter in abcline and letter in commands:
            f2.write(letter+str(abcline[letter])+" ")
        elif letter in abcline:
            f2.write(letter+str(round(abcline[letter],3))+" ")
    f2.write("\n")


f2.close()
print "done"


########NEW FILE########
__FILENAME__ = rename
import glob,os

files=glob.glob("*")
print files
for f in files:
    os.rename(f,f.replace(".ipt","").replace(".iam",""))

########NEW FILE########
__FILENAME__ = reorient
import math, struct, glob

class facet:
    def __init__(self,p1,p2,p3):
        self.p1=p1
        self.p2=p2
        self.p3=p3
    def __getitem__(self,i):
        if i==0:
            return self.p1
        elif i==1:
            return self.p2
        elif i==2:
            return self.p3
        else:
            raise IndexError
    def __len__(self):
        return 3
    def get_normal(self):
        (x1,y1,z1),(x2,y2,z2),(x3,y3,z3)=self
        ux,uy,uz=x2-x1,y2-y1,z2-z1
        vx,vy,vz=x3-x1,y3-y1,z3-z1
        x,y,z=uy*vz-uz*vy,uz*vx-ux*vz,ux*vy-uy*vx
        l=math.sqrt(x*x+y*y+z*z)
        x,y,z=x/l,y/l,z/l
        return (x,y,z)
    def angle(self):
        x,y,z=self.get_normal()
        return 90-math.degrees(math.acos(z))
    def midPoints(self):
        (x1,y1,z1),(x2,y2,z2),(x3,y3,z3)=self
        return ((x1+x2)/2,(y1+y2)/2,(z1+z2)/2),((x3+x2)/2,(y3+y2)/2,(z3+z2)/2),((x1+x3)/2,(y1+y3)/2,(z1+z3)/2)
    def get_maxl(self):
        (x1,y1,z1),(x2,y2,z2),(x3,y3,z3)=self
        l1=math.sqrt((x1-x2)**2+(y1-y2)**2+(z1-z2)**2)
        l2=math.sqrt((x1-x3)**2+(y1-y3)**2+(z1-z3)**2)
        l3=math.sqrt((x3-x2)**2+(y3-y2)**2+(z3-z2)**2)
        return max(l1,l2,l3)
    def transform(self,func):
        self.p1=func(self.p1)
        self.p2=func(self.p2)
        self.p3=func(self.p3)
    def projectedArea(self):
        (x1,y1,z1),(x2,y2,z2),(x3,y3,z3)=self
        a=math.sqrt((x1-x2)**2+(y1-y2)**2)
        b=math.sqrt((x3-x2)**2+(y3-y2)**2)
        c=math.sqrt((x1-x3)**2+(y1-y3)**2)
        s=.5*(a+b+c)
        return math.sqrt(s*(s-a)*(s-b)*(s-c))

class solid:
    def __init__(self,filename):
        f=file(filename)
        text=f.read()
        self.facets=[]
        if "vertex" in text and "outer loop" in text and "facet normal" in text:
            
            text_facets=text.split("facet normal")[1:]
            for text_facet in text_facets:
                points=text_facet.split()[6:-2]
                p1=[float(x) for x in points[0:3]]
                p2=[float(x) for x in points[4:7]]
                p3=[float(x) for x in points[8:11]]
                self.facets.append(facet(p1,p2,p3))
        else:
            f.close()
            f=file(filename,"rb")
            f.read(80)
            n=struct.unpack("I",f.read(4))[0]
            for i in xrange(n):
                facetdata=f.read(50)
                try:
                    data=struct.unpack("12f1H",facetdata)
                    normal=data[0:3]
                    v1=data[3:6]
                    v2=data[6:9]
                    v3=data[9:12]
                    self.facets.append(facet(v1,v2,v3))
                except:
                    print "ERROR REPORT"
                    print [ord(c) for c in facetdata]
                    print "facet number:",i
                    print "facet count:", n
                    

    def getBounds(self):
        p1=list(self.facets[0][0])
        p2=list(self.facets[0][0])
        for f in self.facets:
            for v in f:
                for i in range(3):
                    if v[i]<p1[i]:
                        p1[i]=v[i]
                    if v[i]>p2[i]:
                        p2[i]=v[i]
        return p1,p2

    def printRating(self,minAngle=-60):
        (x,y,minz),p2=self.getBounds()
        c=0
        base=0
        for f in self.facets:
            (x1,y1,z1),(x2,y2,z2),(x3,y3,z3)=f
            if abs(minz-z1)<.1 and abs(minz-z2)<.1 and abs(minz-z3)<.1:
                base+=f.projectedArea()
            elif f.angle()<minAngle:
                c+=f.projectedArea()*abs(minz-z1)
        return c,base

    def getSize(self):
        p1,p2=self.getBounds()
        x1,y1,z1=p1
        x2,y2,z2=p2
        return x2-x1,y2-y1,z2-z1
    

    def sub_divide(self,d=1):
        nfacets=[]
        again=False
        l=0
        for f in self.facets:
            p1,p2,p3=f
            if f.get_maxl()<d:
                nfacets.append(f)
            else:
                if l<f.get_maxl():
                    l=f.get_maxl()
                again=True
                p12,p23,p31=f.midPoints()
                nfacets.append(facet(p1,p12,p31))
                nfacets.append(facet(p2,p23,p12))
                nfacets.append(facet(p3,p31,p23))
                nfacets.append(facet(p12,p23,p31))
        self.facets=nfacets
        if again:
            self.sub_divide(d)

    def transform(self,func):
        for f in self.facets:
            f.transform(func)

    def rotX(self):
        for f in self.facets:
            f.transform(lambda (x,y,z): (x,z,-y))
            
    def rotY(self):
        for f in self.facets:
            f.transform(lambda (x,y,z): (z,y,-x))

    def zero(self):
        (x1,y1,z1),p2=self.getBounds()
        for f in self.facets:
            f.transform(lambda (x,y,z): (x-x1,y-y1,z-z1))

    def save(self,filename,ascii=False):
        self.zero()
        if ascii:
            output="solid "+filename.split(".")[0]+"\n"
            for face in self.facets:
                nx,ny,nz=face.get_normal()
                (x1,y1,z1),(x2,y2,z2),(x3,y3,z3)=face
                output+="  facet normal "+str(nx)+" "+str(ny)+" "+str(nz)+"\n"
                output+="    outer loop\n"
                output+="      vertex "+str(x1)+" "+str(y1)+" "+str(z1)+"\n"
                output+="      vertex "+str(x2)+" "+str(y2)+" "+str(z2)+"\n"
                output+="      vertex "+str(x3)+" "+str(y3)+" "+str(z3)+"\n"
                output+="    endloop\n"
                output+="  endfacet\n"
            f=file(filename,"w")
            f.write(output)
            f.close()
        else:
            f=file(filename,"wb")
            f.write(("STLB "+filename).ljust(80))
            f.write(struct.pack("I",len(self.facets)))
            for face in self.facets:
                nx,ny,nz=face.get_normal()
                (x1,y1,z1),(x2,y2,z2),(x3,y3,z3)=face
                f.write(struct.pack("12f1H",nx,ny,nz,x1,y1,z1,x2,y2,z2,x3,y3,z3,0))
            f.close



def getBestOrientation(s):
    best_cost,best_base=s.printRating()
    for i in range(4):
        cost,base=s.printRating()
        if base>0 and cost<best_cost:
            best_cost=cost
            best_base=base
        if base>best_base and cost==best_cost:
            best_base=base
        s.rotX()
    for i in range(4):
        cost,base=s.printRating()
        if base>0 and cost<best_cost:
            best_cost=cost
            best_base=base
        if base>best_base and cost==best_cost:
            best_base=base
        s.rotY()
    for i in range(4):
        cost,base=s.printRating()
        if cost==best_cost and base==best_base:
            return s
        s.rotX()
    for i in range(4):
        cost,base=s.printRating()
        if cost==best_cost and base==best_base:
            return s
        s.rotY()
    

solids=glob.glob("*.stl")
for sname in solids:
    if sname[:4]!="mod_":
        print "Processing:",sname
        s=solid(sname)
        getBestOrientation(s)
        s.save(sname)


########NEW FILE########
__FILENAME__ = simpson segmentize
#!/usr/bin/env python2
#THIS IS A ConceptFORGE PRODUCT.
#GPL LICENSE

#EXPERIMENTAL.  THIS CODE NEEDS IMPROVEMENT.

#ALL LENGTHS ARE IN mm

#A LIST OF MACHINE POSITIONS WHERE PAPER CAN
#BARELY SLIDE BETWEEN THE BED AND THE EXTRUDER.
#THIS NEEDS TO COVER THE AREA YOU WANT TO PRINT.
#THE MORE THE BETTER.
#EXPECT THE MACHINE TO NEED TO BE RECALIBRATED OFTEN AS
#THE SYSTEM GETS WORKED IN.
POINTS=[(172.5,96,125),#
        (96,167.0,125),#
        (96,125,166.6),#
        (172.9,125,96),#
        (125,169.9,96),#
        (125,96,168.8),#
        ]

#DISTANCE FROM SHOULDER SCREW TO SHOULDER SCREW
SIZE=250.0

#APPROXIMATE Z DISTANCE FROM SHOULDER ARM ATTACHMENT
#TO HUB ARM ATTACHMENT
BED_Z=70

#APPROXIMATE MAX ACTUATED LENGTH OF ARM
MAX_ARM_LENGTH=300

#HOW SMALL SHOULD THE LINE SEGMENTS BE BROKEN DOWN TO?
#SMALL=BETTER QUALITY
#LARGE=SMALLER FILE/FASTER
SEGMENT_SIZE=1.0


from scipy.optimize import leastsq
import numpy.linalg
import math, random, copy, sys

if len(sys.argv)<1:
    f=file(raw_input("Input File: "))
    f2=file(raw_input("Output File: "),"w")
else:
    f=file(sys.argv[1])
    if len(sys.argv) == 2 :
        f2=file(sys.argv[1].split(".")[0] + "-GUS.gcode", "w")		#Automatically name output file like "file.gcode-gus.gcode if no output name was typed"
    else:
        f2=file(sys.argv[2],"w")                                #Guizmo: added the "w" parameter.

        if len(sys.argv) == 4:   
            SEGMENT_SIZE = float(sys.argv[3])  		        #Let the user select segment size as a third argument

DEFAULT_VALUES=[BED_Z,BED_Z,BED_Z,MAX_ARM_LENGTH,MAX_ARM_LENGTH,MAX_ARM_LENGTH]

SHOULDER_Z1,SHOULDER_Z2,SHOULDER_Z3,MAX_LENGTH_1,MAX_LENGTH_2,MAX_LENGTH_3=DEFAULT_VALUES

#GET COORDINATES USING TRILATERATION
def getxyz(r1,r2,r3):
    d=SIZE*1.0
    i=SIZE/2.0
    j=SIZE*math.sqrt(3)/2.0
    x=(r1*r1-r2*r2+d*d)/(2*d)
    y=(r1*r1-r3*r3-x*x+(x-i)**2+j*j)/(2*j)
    z=math.sqrt(r1*r1-x*x-y*y)
    return x,y,z

#GET VALUES FOR EACH POINT TO SEE HOW CLOSE TO THE PLANE IT IS
def equations(p):
    SHOULDER_Z1,SHOULDER_Z2,SHOULDER_Z3,MAX_LENGTH_1,MAX_LENGTH_2,MAX_LENGTH_3=p
    m=[]
    for i in range(len(POINTS)):
        R1,R2,R3=MAX_LENGTH_1-POINTS[i][0],MAX_LENGTH_2-POINTS[i][1],MAX_LENGTH_3-POINTS[i][2]
        X,Y,Z=getxyz(R1,R2,R3)
        d=SIZE*1.0
        i=SIZE/2.0
        j=SIZE*math.sqrt(3)/2.0
        q=[[0,0,SHOULDER_Z1,1],
           [d,0,SHOULDER_Z2,1],
           [i,j,SHOULDER_Z3,1],
           [X,Y,Z,1]]
        det=numpy.linalg.det(q)
        m.append(det**2)
    return m

#GET OPTIMAL VALUES
SHOULDER_Z1,SHOULDER_Z2,SHOULDER_Z3,MAX_LENGTH_1,MAX_LENGTH_2,MAX_LENGTH_3=leastsq(equations, DEFAULT_VALUES)[0]



x1=-SIZE/2.0
y1=-SIZE*math.sqrt(3)/2.0/3.0
z1=-SHOULDER_Z1
x2=+SIZE/2.0
y2=-SIZE*math.sqrt(3)/2.0/3.0
z2=-SHOULDER_Z2
x3=0
y3=2*SIZE*math.sqrt(3)/2.0/3.0
z3=-SHOULDER_Z3
x0,y0,z0=getxyz(MAX_LENGTH_1,MAX_LENGTH_2,MAX_LENGTH_3)
coord={"X":x0+x1,"Y":y0+y1,"Z":z0+z1, "E":0, "F":0}


def getABC(position1):
    if "X" not in position1:
        return position1
    position=copy.deepcopy(position1)
    d=distance(coord,position)
    xs,ys,zs=coord["X"],coord["Y"],coord["Z"]
    x,y,z,f=position["X"],position["Y"],position["Z"],position["F"]
    a1=MAX_LENGTH_1-math.sqrt((xs-x1)**2+(ys-y1)**2+(zs-z1)**2)
    b1=MAX_LENGTH_2-math.sqrt((xs-x2)**2+(ys-y2)**2+(zs-z2)**2)
    c1=MAX_LENGTH_3-math.sqrt((xs-x3)**2+(ys-y3)**2+(zs-z3)**2)
    a2=MAX_LENGTH_1-math.sqrt((x-x1)**2+(y-y1)**2+(z-z1)**2)
    b2=MAX_LENGTH_2-math.sqrt((x-x2)**2+(y-y2)**2+(z-z2)**2)
    c2=MAX_LENGTH_3-math.sqrt((x-x3)**2+(y-y3)**2+(z-z3)**2)
    virtual_d=math.sqrt((a1-a2)**2+(b1-b2)**2+(c1-c2)**2)
    fnew=f
    if d!=0:
        fnew=f*virtual_d/d
    position['X']=a2
    position['Y']=b2
    position['Z']=c2
    position['F']=fnew
    return position

def distance(start, end):
    try:
        x1,y1,z1=start['X'],start['Y'],start['Z']
        x2,y2,z2=end['X'],end['Y'],end['Z']
        return math.sqrt((x1-x2)**2+(y1-y2)**2+(z1-z2)**2)
    except:
        return 0

def interpolate(start, end, i, n):
    x1,y1,z1,e1=start['X'],start['Y'],start['Z'],start['E']
    x2,y2,z2,e2=end['X'],end['Y'],end['Z'],end['E']
    middle={}
    for c in end:
        if c in end and c in start and c!="F":
            middle[c]=(i*end[c]+(n-i)*start[c])/n
        else:
            middle[c]=end[c]
    return middle

def segmentize(start,end,maxLength):
    l=distance(start,end)
    if l<=maxLength:
        return [end]
    else:
        output=[]
        n=int(math.ceil(l/maxLength))
        for i in range(1,n+1):
            output.append(interpolate(start,end,i,n))
        return output

print getABC({"X":45,"Y":0,"Z":1,"F":123})
print getABC({"X":90,"Y":0,"Z":1,"F":123})


prefixes="MGXYZESF"
commands="MG"

program=[]
move_count=0
for line in f:
    line=line.upper()
    line=line.strip()
    chunks=line.split(";")[0].split(" ")
    stuff={}
    for chunk in chunks:
        if len(chunk)>1:
            stuff[chunk[0]]=chunk[1:]
            try:
                stuff[chunk[0]]=int(stuff[chunk[0]])
            except:
                try:
                    stuff[chunk[0]]=float(stuff[chunk[0]])
                except:
                    pass
        if "X" in stuff or "Y" in stuff or "Z" in stuff:
            move_count+=1
            for c in coord:
                if c not in stuff:
                    stuff[c]=coord[c]           
    if move_count<=3 and len(stuff)>0:
        program+=[stuff]
    elif len(stuff)>0:
        segments=segmentize(coord,stuff,SEGMENT_SIZE)
        program+=segments
    for c in coord:
        if c in stuff:
            coord[c]=stuff[c]
f2.write("G92 X0 Y0 Z0 E0\nG1 X-1000 Y-1000 Z-1000\nG28\n")
for line in program:
    abcline=getABC(line)
    for letter in prefixes:
        if letter in abcline and letter in commands:
            f2.write(letter+str(abcline[letter])+" ")
        elif letter in abcline:
            f2.write(letter+str(round(abcline[letter],3))+" ")
    f2.write("\n")


f2.close()
print "done"


########NEW FILE########
__FILENAME__ = rename
import glob,os

files=glob.glob("*")
print files
for f in files:
    os.rename(f,f.replace(".ipt",""))

########NEW FILE########
__FILENAME__ = reorient
import math, struct, glob

class facet:
    def __init__(self,p1,p2,p3):
        self.p1=p1
        self.p2=p2
        self.p3=p3
    def __getitem__(self,i):
        if i==0:
            return self.p1
        elif i==1:
            return self.p2
        elif i==2:
            return self.p3
        else:
            raise IndexError
    def __len__(self):
        return 3
    def get_normal(self):
        (x1,y1,z1),(x2,y2,z2),(x3,y3,z3)=self
        ux,uy,uz=x2-x1,y2-y1,z2-z1
        vx,vy,vz=x3-x1,y3-y1,z3-z1
        x,y,z=uy*vz-uz*vy,uz*vx-ux*vz,ux*vy-uy*vx
        l=math.sqrt(x*x+y*y+z*z)
        x,y,z=x/l,y/l,z/l
        return (x,y,z)
    def angle(self):
        x,y,z=self.get_normal()
        return 90-math.degrees(math.acos(z))
    def midPoints(self):
        (x1,y1,z1),(x2,y2,z2),(x3,y3,z3)=self
        return ((x1+x2)/2,(y1+y2)/2,(z1+z2)/2),((x3+x2)/2,(y3+y2)/2,(z3+z2)/2),((x1+x3)/2,(y1+y3)/2,(z1+z3)/2)
    def get_maxl(self):
        (x1,y1,z1),(x2,y2,z2),(x3,y3,z3)=self
        l1=math.sqrt((x1-x2)**2+(y1-y2)**2+(z1-z2)**2)
        l2=math.sqrt((x1-x3)**2+(y1-y3)**2+(z1-z3)**2)
        l3=math.sqrt((x3-x2)**2+(y3-y2)**2+(z3-z2)**2)
        return max(l1,l2,l3)
    def transform(self,func):
        self.p1=func(self.p1)
        self.p2=func(self.p2)
        self.p3=func(self.p3)
    def projectedArea(self):
        (x1,y1,z1),(x2,y2,z2),(x3,y3,z3)=self
        a=math.sqrt((x1-x2)**2+(y1-y2)**2)
        b=math.sqrt((x3-x2)**2+(y3-y2)**2)
        c=math.sqrt((x1-x3)**2+(y1-y3)**2)
        s=.5*(a+b+c)
        return math.sqrt(s*(s-a)*(s-b)*(s-c))

class solid:
    def __init__(self,filename):
        f=file(filename)
        text=f.read()
        self.facets=[]
        if "vertex" in text and "outer loop" in text and "facet normal" in text:
            
            text_facets=text.split("facet normal")[1:]
            for text_facet in text_facets:
                points=text_facet.split()[6:-2]
                p1=[float(x) for x in points[0:3]]
                p2=[float(x) for x in points[4:7]]
                p3=[float(x) for x in points[8:11]]
                self.facets.append(facet(p1,p2,p3))
        else:
            f.close()
            f=file(filename,"rb")
            f.read(80)
            n=struct.unpack("I",f.read(4))[0]
            for i in xrange(n):
                facetdata=f.read(50)
                try:
                    data=struct.unpack("12f1H",facetdata)
                    normal=data[0:3]
                    v1=data[3:6]
                    v2=data[6:9]
                    v3=data[9:12]
                    self.facets.append(facet(v1,v2,v3))
                except:
                    print "ERROR REPORT"
                    print [ord(c) for c in facetdata]
                    print "facet number:",i
                    print "facet count:", n
                    

    def getBounds(self):
        p1=list(self.facets[0][0])
        p2=list(self.facets[0][0])
        for f in self.facets:
            for v in f:
                for i in range(3):
                    if v[i]<p1[i]:
                        p1[i]=v[i]
                    if v[i]>p2[i]:
                        p2[i]=v[i]
        return p1,p2

    def printRating(self,minAngle=-60):
        (x,y,minz),p2=self.getBounds()
        c=0
        base=0
        for f in self.facets:
            (x1,y1,z1),(x2,y2,z2),(x3,y3,z3)=f
            if abs(minz-z1)<.1 and abs(minz-z2)<.1 and abs(minz-z3)<.1:
                base+=f.projectedArea()
            elif f.angle()<minAngle:
                c+=f.projectedArea()*abs(minz-z1)
        return c,base

    def getSize(self):
        p1,p2=self.getBounds()
        x1,y1,z1=p1
        x2,y2,z2=p2
        return x2-x1,y2-y1,z2-z1
    

    def sub_divide(self,d=1):
        nfacets=[]
        again=False
        l=0
        for f in self.facets:
            p1,p2,p3=f
            if f.get_maxl()<d:
                nfacets.append(f)
            else:
                if l<f.get_maxl():
                    l=f.get_maxl()
                again=True
                p12,p23,p31=f.midPoints()
                nfacets.append(facet(p1,p12,p31))
                nfacets.append(facet(p2,p23,p12))
                nfacets.append(facet(p3,p31,p23))
                nfacets.append(facet(p12,p23,p31))
        self.facets=nfacets
        if again:
            self.sub_divide(d)

    def transform(self,func):
        for f in self.facets:
            f.transform(func)

    def rotX(self):
        for f in self.facets:
            f.transform(lambda (x,y,z): (x,z,-y))
            
    def rotY(self):
        for f in self.facets:
            f.transform(lambda (x,y,z): (z,y,-x))

    def zero(self):
        (x1,y1,z1),p2=self.getBounds()
        for f in self.facets:
            f.transform(lambda (x,y,z): (x-x1,y-y1,z-z1))

    def save(self,filename,ascii=False):
        self.zero()
        if ascii:
            output="solid "+filename.split(".")[0]+"\n"
            for face in self.facets:
                nx,ny,nz=face.get_normal()
                (x1,y1,z1),(x2,y2,z2),(x3,y3,z3)=face
                output+="  facet normal "+str(nx)+" "+str(ny)+" "+str(nz)+"\n"
                output+="    outer loop\n"
                output+="      vertex "+str(x1)+" "+str(y1)+" "+str(z1)+"\n"
                output+="      vertex "+str(x2)+" "+str(y2)+" "+str(z2)+"\n"
                output+="      vertex "+str(x3)+" "+str(y3)+" "+str(z3)+"\n"
                output+="    endloop\n"
                output+="  endfacet\n"
            f=file(filename,"w")
            f.write(output)
            f.close()
        else:
            f=file(filename,"wb")
            f.write(("STLB "+filename).ljust(80))
            f.write(struct.pack("I",len(self.facets)))
            for face in self.facets:
                nx,ny,nz=face.get_normal()
                (x1,y1,z1),(x2,y2,z2),(x3,y3,z3)=face
                f.write(struct.pack("12f1H",nx,ny,nz,x1,y1,z1,x2,y2,z2,x3,y3,z3,0))
            f.close



def getBestOrientation(s):
    best_cost,best_base=s.printRating()
    for i in range(4):
        cost,base=s.printRating()
        if base>0 and cost<best_cost:
            best_cost=cost
            best_base=base
        if base>best_base and cost==best_cost:
            best_base=base
        s.rotX()
    for i in range(4):
        cost,base=s.printRating()
        if base>0 and cost<best_cost:
            best_cost=cost
            best_base=base
        if base>best_base and cost==best_cost:
            best_base=base
        s.rotY()
    for i in range(4):
        cost,base=s.printRating()
        if cost==best_cost and base==best_base:
            return s
        s.rotX()
    for i in range(4):
        cost,base=s.printRating()
        if cost==best_cost and base==best_base:
            return s
        s.rotY()
    

solids=glob.glob("*.stl")
for sname in solids:
    if sname[:4]!="mod_":
        print "Processing:",sname
        s=solid(sname)
        getBestOrientation(s)
        s.save(sname)


########NEW FILE########
__FILENAME__ = simpson segmentize
#!/usr/bin/env python2
import math,copy

"""PARAMETERS"""
shoulder_offset=37.5
hub_offset=50
arm_length=200
screw_spacing=300
screw_angles=[150,270,30]
start_positions=[253.2,252.9,253.2] #G92 X253.75 Y253.75 Z253.75

delta_radius=screw_spacing/3.0*math.sqrt(3)
screw_positions=[(delta_radius*math.cos(math.pi*screw_angles[i]/180.0),delta_radius*math.sin(math.pi*screw_angles[i]/180.0)) for i in range(3)]

coord={"X":0,"Y":0,"Z":0, "E":0, "F":1200}

f=file(raw_input("Input File: "))

def transform_raw(x,y,z):
    thetas=[(((+.5-math.atan2(y-screw_positions[i][1],x-screw_positions[i][0])/2/math.pi+screw_angles[i]/360.0)+.5)%1-.5)*25.4 for i in range(3)]
    ds=[math.sqrt((x-screw_positions[i][0])**2+(y-screw_positions[i][1])**2) for i in range(3)]
    try:
        return [z+thetas[i]+math.sqrt(arm_length**2-(ds[i]-hub_offset-shoulder_offset)**2) for i in range(3)]
    except:
        print x,y,z
def transform(x,y,z):
    A,B,C=transform_raw(0,0,0)
    a,b,c=transform_raw(x,y,z)
    return a-A,b-B,c-C
#print "G1","X"+str(x-X),"Y"+str(y-Y),"Z"+str(z-Z)
print transform(0,0,0)
def getABC(position1):
    if "X" not in position1:
        return position1
    position=copy.deepcopy(position1)
    xs,ys,zs=coord["X"],coord["Y"],coord["Z"]
    x,y,z,f=position["X"],position["Y"],position["Z"],position["F"]
    a1,b1,c1=transform(xs,ys,zs)
    a2,b2,c2=transform(x,y,z)
    virtual_d=math.sqrt((a1-a2)**2+(b1-b2)**2+(c1-c2)**2)
    d=math.sqrt((x-xs)**2+(y-ys)**2+(z-zs)**2)
    fnew=f
    if d!=0:
        fnew=f*virtual_d/d
    position['X']=a2
    position['Y']=b2
    position['Z']=c2
    position['F']=fnew
    return position




def distance(start, end):
    try:
        x1,y1,z1=start['X'],start['Y'],start['Z']
        x2,y2,z2=end['X'],end['Y'],end['Z']
        return math.sqrt((x1-x2)**2+(y1-y2)**2+(z1-z2)**2)
    except:
        return 0

def interpolate(start, end, i, n):
    x1,y1,z1,e1=start['X'],start['Y'],start['Z'],start['E']
    x2,y2,z2,e2=end['X'],end['Y'],end['Z'],end['E']
    middle={}
    for c in end:
        if c in end and c in start and c!="F":
            middle[c]=(i*end[c]+(n-i)*start[c])/n
        else:
            middle[c]=end[c]
    return middle

def segmentize(start,end,maxLength):
    l=distance(start,end)
    if l<=maxLength:
        return [end]
    else:
        output=[]
        n=int(math.ceil(l/maxLength))
        for i in range(1,n+1):
            output.append(interpolate(start,end,i,n))
        return output
            
    



prefixes="MGXYZESF"
commands="MG"
f2=file(raw_input("Output File: "),"w")
f2.write("G92 X"+str(start_positions[0])+" Y"+str(start_positions[1])+" Z"+str(start_positions[2])+" E0\n")
program=[]
move_count=0
for line in f:
    line=line.strip()
    chunks=line.split(";")[0].split(" ")
    stuff={}
    for chunk in chunks:
        if len(chunk)>1:
            stuff[chunk[0]]=chunk[1:]
            try:
                stuff[chunk[0]]=int(stuff[chunk[0]])
            except:
                try:
                    stuff[chunk[0]]=float(stuff[chunk[0]])
                except:
                    pass
        if "X" in stuff or "Y" in stuff or "Z" in stuff:
            move_count+=1
            for c in coord:
                if c not in stuff:
                    stuff[c]=coord[c]           
    if move_count<=3 and len(stuff)>0:
        program+=[stuff]
    elif len(stuff)>0:
        segments=segmentize(coord,stuff,1)
        program+=segments
    for c in coord:
        if c in stuff:
            coord[c]=stuff[c]

for line in program:
    abcline=getABC(line)
    for letter in prefixes:
        if letter in abcline and letter in commands:
            f2.write(letter+str(abcline[letter])+" ")
        elif letter in abcline:
            f2.write(letter+str(round(abcline[letter],3))+" ")
    f2.write("\n")
f2.write("G1 X"+str(start_positions[0])+" Y"+str(start_positions[1])+" Z"+str(start_positions[2])+"\n")


f2.close()
print "done"


########NEW FILE########
__FILENAME__ = rename
import glob,os

files=glob.glob("*")
print files
for f in files:
    os.rename(f,f.replace(".ipt",""))

########NEW FILE########
__FILENAME__ = reorient
import math, struct, glob

class facet:
    def __init__(self,p1,p2,p3):
        self.p1=p1
        self.p2=p2
        self.p3=p3
    def __getitem__(self,i):
        if i==0:
            return self.p1
        elif i==1:
            return self.p2
        elif i==2:
            return self.p3
        else:
            raise IndexError
    def __len__(self):
        return 3
    def get_normal(self):
        (x1,y1,z1),(x2,y2,z2),(x3,y3,z3)=self
        ux,uy,uz=x2-x1,y2-y1,z2-z1
        vx,vy,vz=x3-x1,y3-y1,z3-z1
        x,y,z=uy*vz-uz*vy,uz*vx-ux*vz,ux*vy-uy*vx
        l=math.sqrt(x*x+y*y+z*z)
        x,y,z=x/l,y/l,z/l
        return (x,y,z)
    def angle(self):
        x,y,z=self.get_normal()
        return 90-math.degrees(math.acos(z))
    def midPoints(self):
        (x1,y1,z1),(x2,y2,z2),(x3,y3,z3)=self
        return ((x1+x2)/2,(y1+y2)/2,(z1+z2)/2),((x3+x2)/2,(y3+y2)/2,(z3+z2)/2),((x1+x3)/2,(y1+y3)/2,(z1+z3)/2)
    def get_maxl(self):
        (x1,y1,z1),(x2,y2,z2),(x3,y3,z3)=self
        l1=math.sqrt((x1-x2)**2+(y1-y2)**2+(z1-z2)**2)
        l2=math.sqrt((x1-x3)**2+(y1-y3)**2+(z1-z3)**2)
        l3=math.sqrt((x3-x2)**2+(y3-y2)**2+(z3-z2)**2)
        return max(l1,l2,l3)
    def transform(self,func):
        self.p1=func(self.p1)
        self.p2=func(self.p2)
        self.p3=func(self.p3)
    def projectedArea(self):
        (x1,y1,z1),(x2,y2,z2),(x3,y3,z3)=self
        a=math.sqrt((x1-x2)**2+(y1-y2)**2)
        b=math.sqrt((x3-x2)**2+(y3-y2)**2)
        c=math.sqrt((x1-x3)**2+(y1-y3)**2)
        s=.5*(a+b+c)
        return math.sqrt(s*(s-a)*(s-b)*(s-c))

class solid:
    def __init__(self,filename):
        f=file(filename)
        text=f.read()
        self.facets=[]
        if "vertex" in text and "outer loop" in text and "facet normal" in text:
            
            text_facets=text.split("facet normal")[1:]
            for text_facet in text_facets:
                points=text_facet.split()[6:-2]
                p1=[float(x) for x in points[0:3]]
                p2=[float(x) for x in points[4:7]]
                p3=[float(x) for x in points[8:11]]
                self.facets.append(facet(p1,p2,p3))
        else:
            f.close()
            f=file(filename,"rb")
            f.read(80)
            n=struct.unpack("I",f.read(4))[0]
            for i in xrange(n):
                facetdata=f.read(50)
                try:
                    data=struct.unpack("12f1H",facetdata)
                    normal=data[0:3]
                    v1=data[3:6]
                    v2=data[6:9]
                    v3=data[9:12]
                    self.facets.append(facet(v1,v2,v3))
                except:
                    print "ERROR REPORT"
                    print [ord(c) for c in facetdata]
                    print "facet number:",i
                    print "facet count:", n
                    

    def getBounds(self):
        p1=list(self.facets[0][0])
        p2=list(self.facets[0][0])
        for f in self.facets:
            for v in f:
                for i in range(3):
                    if v[i]<p1[i]:
                        p1[i]=v[i]
                    if v[i]>p2[i]:
                        p2[i]=v[i]
        return p1,p2

    def printRating(self,minAngle=-60):
        (x,y,minz),p2=self.getBounds()
        c=0
        base=0
        for f in self.facets:
            (x1,y1,z1),(x2,y2,z2),(x3,y3,z3)=f
            if abs(minz-z1)<.1 and abs(minz-z2)<.1 and abs(minz-z3)<.1:
                base+=f.projectedArea()
            elif f.angle()<minAngle:
                c+=f.projectedArea()*abs(minz-z1)
        return c,base

    def getSize(self):
        p1,p2=self.getBounds()
        x1,y1,z1=p1
        x2,y2,z2=p2
        return x2-x1,y2-y1,z2-z1
    

    def sub_divide(self,d=1):
        nfacets=[]
        again=False
        l=0
        for f in self.facets:
            p1,p2,p3=f
            if f.get_maxl()<d:
                nfacets.append(f)
            else:
                if l<f.get_maxl():
                    l=f.get_maxl()
                again=True
                p12,p23,p31=f.midPoints()
                nfacets.append(facet(p1,p12,p31))
                nfacets.append(facet(p2,p23,p12))
                nfacets.append(facet(p3,p31,p23))
                nfacets.append(facet(p12,p23,p31))
        self.facets=nfacets
        if again:
            self.sub_divide(d)

    def transform(self,func):
        for f in self.facets:
            f.transform(func)

    def rotX(self):
        for f in self.facets:
            f.transform(lambda (x,y,z): (x,z,-y))
            
    def rotY(self):
        for f in self.facets:
            f.transform(lambda (x,y,z): (z,y,-x))

    def zero(self):
        (x1,y1,z1),p2=self.getBounds()
        for f in self.facets:
            f.transform(lambda (x,y,z): (x-x1,y-y1,z-z1))

    def save(self,filename,ascii=False):
        self.zero()
        if ascii:
            output="solid "+filename.split(".")[0]+"\n"
            for face in self.facets:
                nx,ny,nz=face.get_normal()
                (x1,y1,z1),(x2,y2,z2),(x3,y3,z3)=face
                output+="  facet normal "+str(nx)+" "+str(ny)+" "+str(nz)+"\n"
                output+="    outer loop\n"
                output+="      vertex "+str(x1)+" "+str(y1)+" "+str(z1)+"\n"
                output+="      vertex "+str(x2)+" "+str(y2)+" "+str(z2)+"\n"
                output+="      vertex "+str(x3)+" "+str(y3)+" "+str(z3)+"\n"
                output+="    endloop\n"
                output+="  endfacet\n"
            f=file(filename,"w")
            f.write(output)
            f.close()
        else:
            f=file(filename,"wb")
            f.write(("STLB "+filename).ljust(80))
            f.write(struct.pack("I",len(self.facets)))
            for face in self.facets:
                nx,ny,nz=face.get_normal()
                (x1,y1,z1),(x2,y2,z2),(x3,y3,z3)=face
                f.write(struct.pack("12f1H",nx,ny,nz,x1,y1,z1,x2,y2,z2,x3,y3,z3,0))
            f.close



def getBestOrientation(s):
    best_cost,best_base=s.printRating()
    for i in range(4):
        cost,base=s.printRating()
        if base>0 and cost<best_cost:
            best_cost=cost
            best_base=base
        if base>best_base and cost==best_cost:
            best_base=base
        s.rotX()
    for i in range(4):
        cost,base=s.printRating()
        if base>0 and cost<best_cost:
            best_cost=cost
            best_base=base
        if base>best_base and cost==best_cost:
            best_base=base
        s.rotY()
    for i in range(4):
        cost,base=s.printRating()
        if cost==best_cost and base==best_base:
            return s
        s.rotX()
    for i in range(4):
        cost,base=s.printRating()
        if cost==best_cost and base==best_base:
            return s
        s.rotY()
    

solids=glob.glob("*.stl")
for sname in solids:
    if sname[:4]!="mod_":
        print "Processing:",sname
        s=solid(sname)
        getBestOrientation(s)
        s.save(sname)


########NEW FILE########
__FILENAME__ = reorient
import math, struct, glob

class facet:
    def __init__(self,p1,p2,p3):
        self.p1=p1
        self.p2=p2
        self.p3=p3
    def __getitem__(self,i):
        if i==0:
            return self.p1
        elif i==1:
            return self.p2
        elif i==2:
            return self.p3
        else:
            raise IndexError
    def __len__(self):
        return 3
    def get_normal(self):
        (x1,y1,z1),(x2,y2,z2),(x3,y3,z3)=self
        ux,uy,uz=x2-x1,y2-y1,z2-z1
        vx,vy,vz=x3-x1,y3-y1,z3-z1
        x,y,z=uy*vz-uz*vy,uz*vx-ux*vz,ux*vy-uy*vx
        l=math.sqrt(x*x+y*y+z*z)
        x,y,z=x/l,y/l,z/l
        return (x,y,z)
    def angle(self):
        x,y,z=self.get_normal()
        return 90-math.degrees(math.acos(z))
    def midPoints(self):
        (x1,y1,z1),(x2,y2,z2),(x3,y3,z3)=self
        return ((x1+x2)/2,(y1+y2)/2,(z1+z2)/2),((x3+x2)/2,(y3+y2)/2,(z3+z2)/2),((x1+x3)/2,(y1+y3)/2,(z1+z3)/2)
    def get_maxl(self):
        (x1,y1,z1),(x2,y2,z2),(x3,y3,z3)=self
        l1=math.sqrt((x1-x2)**2+(y1-y2)**2+(z1-z2)**2)
        l2=math.sqrt((x1-x3)**2+(y1-y3)**2+(z1-z3)**2)
        l3=math.sqrt((x3-x2)**2+(y3-y2)**2+(z3-z2)**2)
        return max(l1,l2,l3)
    def transform(self,func):
        self.p1=func(self.p1)
        self.p2=func(self.p2)
        self.p3=func(self.p3)
    def projectedArea(self):
        (x1,y1,z1),(x2,y2,z2),(x3,y3,z3)=self
        a=math.sqrt((x1-x2)**2+(y1-y2)**2)
        b=math.sqrt((x3-x2)**2+(y3-y2)**2)
        c=math.sqrt((x1-x3)**2+(y1-y3)**2)
        s=.5*(a+b+c)
        return math.sqrt(s*(s-a)*(s-b)*(s-c))

class solid:
    def __init__(self,filename):
        f=file(filename)
        text=f.read()
        self.facets=[]
        if "vertex" in text and "outer loop" in text and "facet normal" in text:
            
            text_facets=text.split("facet normal")[1:]
            for text_facet in text_facets:
                points=text_facet.split()[6:-2]
                p1=[float(x) for x in points[0:3]]
                p2=[float(x) for x in points[4:7]]
                p3=[float(x) for x in points[8:11]]
                self.facets.append(facet(p1,p2,p3))
        else:
            f.close()
            f=file(filename,"rb")
            f.read(80)
            n=struct.unpack("I",f.read(4))[0]
            for i in xrange(n):
                facetdata=f.read(50)
                try:
                    data=struct.unpack("12f1H",facetdata)
                    normal=data[0:3]
                    v1=data[3:6]
                    v2=data[6:9]
                    v3=data[9:12]
                    self.facets.append(facet(v1,v2,v3))
                except:
                    print "ERROR REPORT"
                    print [ord(c) for c in facetdata]
                    print "facet number:",i
                    print "facet count:", n
                    

    def getBounds(self):
        p1=list(self.facets[0][0])
        p2=list(self.facets[0][0])
        for f in self.facets:
            for v in f:
                for i in range(3):
                    if v[i]<p1[i]:
                        p1[i]=v[i]
                    if v[i]>p2[i]:
                        p2[i]=v[i]
        return p1,p2

    def printRating(self,minAngle=-60):
        (x,y,minz),p2=self.getBounds()
        c=0
        base=0
        for f in self.facets:
            (x1,y1,z1),(x2,y2,z2),(x3,y3,z3)=f
            if abs(minz-z1)<.1 and abs(minz-z2)<.1 and abs(minz-z3)<.1:
                base+=f.projectedArea()
            elif f.angle()<minAngle:
                c+=f.projectedArea()*abs(minz-z1)
        return c,base

    def getSize(self):
        p1,p2=self.getBounds()
        x1,y1,z1=p1
        x2,y2,z2=p2
        return x2-x1,y2-y1,z2-z1
    

    def sub_divide(self,d=1):
        nfacets=[]
        again=False
        l=0
        for f in self.facets:
            p1,p2,p3=f
            if f.get_maxl()<d:
                nfacets.append(f)
            else:
                if l<f.get_maxl():
                    l=f.get_maxl()
                again=True
                p12,p23,p31=f.midPoints()
                nfacets.append(facet(p1,p12,p31))
                nfacets.append(facet(p2,p23,p12))
                nfacets.append(facet(p3,p31,p23))
                nfacets.append(facet(p12,p23,p31))
        self.facets=nfacets
        if again:
            self.sub_divide(d)

    def transform(self,func):
        for f in self.facets:
            f.transform(func)

    def rotX(self):
        for f in self.facets:
            f.transform(lambda (x,y,z): (x,z,-y))
            
    def rotY(self):
        for f in self.facets:
            f.transform(lambda (x,y,z): (z,y,-x))

    def zero(self):
        (x1,y1,z1),p2=self.getBounds()
        for f in self.facets:
            f.transform(lambda (x,y,z): (x-x1,y-y1,z-z1))

    def save(self,filename,ascii=False):
        self.zero()
        if ascii:
            output="solid "+filename.split(".")[0]+"\n"
            for face in self.facets:
                nx,ny,nz=face.get_normal()
                (x1,y1,z1),(x2,y2,z2),(x3,y3,z3)=face
                output+="  facet normal "+str(nx)+" "+str(ny)+" "+str(nz)+"\n"
                output+="    outer loop\n"
                output+="      vertex "+str(x1)+" "+str(y1)+" "+str(z1)+"\n"
                output+="      vertex "+str(x2)+" "+str(y2)+" "+str(z2)+"\n"
                output+="      vertex "+str(x3)+" "+str(y3)+" "+str(z3)+"\n"
                output+="    endloop\n"
                output+="  endfacet\n"
            f=file(filename,"w")
            f.write(output)
            f.close()
        else:
            f=file(filename,"wb")
            f.write(("STLB "+filename).ljust(80))
            f.write(struct.pack("I",len(self.facets)))
            for face in self.facets:
                nx,ny,nz=face.get_normal()
                (x1,y1,z1),(x2,y2,z2),(x3,y3,z3)=face
                f.write(struct.pack("12f1H",nx,ny,nz,x1,y1,z1,x2,y2,z2,x3,y3,z3,0))
            f.close



def getBestOrientation(s):
    best_cost,best_base=s.printRating()
    for i in range(4):
        cost,base=s.printRating()
        if base>0 and cost<best_cost:
            best_cost=cost
            best_base=base
        if base>best_base and cost==best_cost:
            best_base=base
        s.rotX()
    for i in range(4):
        cost,base=s.printRating()
        if base>0 and cost<best_cost:
            best_cost=cost
            best_base=base
        if base>best_base and cost==best_cost:
            best_base=base
        s.rotY()
    for i in range(4):
        cost,base=s.printRating()
        if cost==best_cost and base==best_base:
            return s
        s.rotX()
    for i in range(4):
        cost,base=s.printRating()
        if cost==best_cost and base==best_base:
            return s
        s.rotY()
    

solids=glob.glob("*.stl")
for sname in solids:
    if sname[:4]!="mod_":
        print "Processing:",sname
        s=solid(sname)
        getBestOrientation(s)
        s.save("mod_"+sname)


########NEW FILE########
__FILENAME__ = rename
import glob,os

files=glob.glob("*")
print files
for f in files:
    os.rename(f,f.replace(".ipt",""))

########NEW FILE########
__FILENAME__ = wally segmentize
#!/usr/bin/env python2

import math,copy,turtle,sys

try:
    import numpy
except:
    print "Download numpy."
    raw_input("PRESS ENTER TO EXIT PROGRAM")
    sys.exit()

try:
    import scipy.optimize
    import scipy.interpolate 
    
except:
    print "Download scipy."
    raw_input("PRESS ENTER TO EXIT PROGRAM")
    sys.exit()

#How many mm does the machine think is one rotation of the x or y axis?
mm_rotation=400    

#various machine coordinate sets where the effector barely touches the bed
touch_points=[(820,720,149.90),(820,1370,150.5),(1370,820,151),(1200,1200,150.9),(1350,3600,151.40)] 

#CALIBRATION DATA FOR THE BED HEIGHT
z_machine_actual=[(1,0.08),(2,0.84),(3,1.76),(4,2.68),
                  (5,3.62),(6,4.52),(7,5.45),(8,6.35),
                  (9,7.21),(10,8.13),(11,9.11),(12,10.03),
                  (13,11.05),(14,12.11),(15,13.19),(16,14.3),
                  (17,15.42),(18,16.51),(19,17.61),(20,18.71),
                  (21,19.74),(22,20.72),(23,21.65),(24,22.57),
                  (25,23.5),(26,24.44),(27,25.41),(28,26.39),
                  (29,27.41),(30,28.45),(31,29.51),(32,30.61),
                  (33,31.69),(34,32.77),(35,33.87),(36,34.94),
                  (37,36.01),(38,37.01),(39,37.97),(40,38.97),
                  (41,39.89),(42,40.85),(43,41.81),(44,42.79),
                  (45,43.84),(46,44.88),(47,45.96),(48,47.02),
                  (49,48.11),(50,49.24),(51,50.34),(52,51.42),
                  (53,52.48),(54,53.5),(55,54.5),(56,55.48),
                  (57,56.47),(58,57.43),(59,58.41),(60,59.43),
                  (61,60.48),(62,61.52),(63,62.57),(64,63.65),
                  (65,64.75),(66,65.83),(67,66.94),(68,68.01),
                  (69,69.09),(70,70.13),(71,71.15),(72,72.14),
                  (73,73.1),(74,74.07),(75,75.08),(76,76.08),
                  (77,77.13),(78,78.14),(79,79.19),(80,80.25),
                  (81,81.32),(82,82.38),(83,83.44),(84,84.51),
                  (85,85.58),(86,86.66),(87,87.62),(88,88.6),
                  (89,89.54),(90,90.5),(91,91.47),(92,92.45),
                  (93,93.47),(94,94.5),(95,95.55),(96,96.6),
                  (97,97.62),(98,98.65),(99,99.72),(100,100.76),
                  (101,101.83),(102,102.86),(103,103.85),(104,104.85),
                  (105,105.81),(106,106.8),(107,107.72),(108,108.68),
                  (109,109.7),(110,110.7),(111,111.71),(112,112.73),
                  (113,113.75),(114,114.76),(115,115.8),(116,116.84),
                  (117,117.87),(118,118.88),(119,119.87),(120,120.85),
                  (121,121.74),(122,122.73),(123,123.63),(124,124.54),
                  (125,125.49),(126,126.46),(127,127.42),(128,128.4),
                  (129,129.39),(130,130.39),(131,131.4),(132,132.32),
                  (133,133.42),(134,134.44),(135,135.42),(136,136.4),
                  (137,137.37),(138,138.29),(139,139.2),(140,140.1),
                  (141,141.05),(142,141.97),(143,142.95),(144,143.89),
                  (145,144.87),(146,145.85),(147,146.86),(148,147.85),
                  (149,148.87),(150,149.86),(151,150.86),(152,151.87),
                  (153,152.84),(154,153.77),(155,154.68),(156,155.57)]

#the z height where the bed arms are at 90 degrees
square_z=76.97

#LENGTH OF ARMS
l=150

#DISTANCE BETWEEN SHOULDERS
L=250

#DISTANCE FROM BED ARM ATTACHMENT TO THE CENTER OF THE BED IN THE Y DIRECTION
y_offset=37.5

#Using "G1 X? Y?" to find the machine coordinates that make the arms colinear
straight_forearms=996 


machine_z=numpy.array([i for i,j in z_machine_actual])
actual_z=numpy.array([j for i,j in z_machine_actual])
square_z=float(square_z)
l=float(l)
L=float(L)
y_offset=float(y_offset)
straight_forearms=float(straight_forearms)
mm_rotation=float(mm_rotation)
mechanical_advantage=(straight_forearms/(mm_rotation/2)*math.pi+math.asin(1-L/2.0/l)+math.asin(L/4.0/l))/(math.pi-math.acos(1-L/2.0/l))




def interpolate2(v,leftLookup=True):
    try:
        x=machine_z
        y=actual_z
        if leftLookup:
            f = scipy.interpolate.interp1d(x, y)#, kind='cubic')
        else:
            f = scipy.interpolate.interp1d(y,x)
        return float(f(v))
    except:
        return 0

    """total_weight=0
    new_v=0
    table.sort()
    for m,a in table:
        if not leftLookup:
            m,a=a,m
        if m!=v:
            weight=1.0/(m-v)**2
        else:
            weight=100.0
        new_v+=weight*a
        total_weight+=weight
    return new_v/total_weight"""
#print interpolate2(0)



def machine2reference((x,y,z)):
    zprime=interpolate2(z)
    def func((i,j)):
        (x2,y2,z2)=reference2machine((i,j,0))
        return (x-x2)**2+(y-y2)**2
    xprime,yprime=scipy.optimize.fmin(func,(100,-100), xtol=0.000001, ftol=0.000001,disp=False)
    return xprime,yprime,zprime
    
def reference2machine((x,y,z)):
    try:
        zprime=interpolate2(z,False)
        initial_angle=math.acos(L/(4*l))
        left_leg=math.sqrt(x*x+y*y)
        right_leg=math.sqrt((L-x)*(L-x)+y*y)
        left_elbow=math.acos((left_leg*left_leg-2*l*l)/(-2*l*l))
        right_elbow=math.acos((right_leg*right_leg-2*l*l)/(-2*l*l))
        left_small_angle=(math.pi-left_elbow)/2
        right_small_angle=(math.pi-right_elbow)/2
        left_virtual=math.atan(-y/x)
        right_virtual=math.atan(-y/(L-x))
        left_drive=left_small_angle+left_virtual-initial_angle
        right_drive=right_small_angle+right_virtual-initial_angle
        left_stepper=-left_drive+(math.pi-left_elbow)*mechanical_advantage
        right_stepper=-right_drive+(math.pi-right_elbow)*mechanical_advantage
        return left_stepper*mm_rotation/2/math.pi,right_stepper*mm_rotation/2/math.pi,zprime
    except:
        return 0,0,0

def refPlane():
    ref_points=[(machine2reference(p)) for p in touch_points]
    #print ref_points
    def func((a,b,c,d)):
        v=0
        for x,y,z in ref_points:
            v+=(a*x+b*y+c*z+d)**2
        return v
    a,b,c,d=scipy.optimize.fmin(func,(1,1,1,1),disp=False)
    return a,b,c,d

print "Finding bed level from touch points.  This may take a while."
ap,bp,cp,dp=refPlane()
#print ap,bp,cp,dp

#print machine2reference((1000,1000,100))
#print reference2machine((125,125,100))
def actual2reference((x,y,z)):
    bed_angle=math.asin((z-interpolate2(square_z))/l)
    leg_offset=l*math.cos(bed_angle)
    yprime=y+y_offset-leg_offset
    xprime=x+L/2
    zero_z=(-dp-ap*xprime-bp*yprime)/cp
    #print xprime,yprime,zero_z
    zprime=zero_z-z
    return xprime,yprime,zprime
#print actual2reference((0,0,0))

def reference2actual((x,y,z)):
    pass

def transform(x,y,z):
    return reference2machine(actual2reference((x,y,z)))
#print transform(0,0,0)

def testcode(x,y,z):
    a,b,c=transform(x,y,z)
    #print transform(x,y,z)
    return "G1 X"+str(a)+" Y"+str(b)+" Z"+str(c)+" F9000"
#print testcode(0,0,0)

def getABC(position1):
    global coord
    if "X" not in position1:
        return position1
    position=copy.deepcopy(position1)
    d=distance(coord,position)
    f=position["F"]
    a1,b1,c1=transform(coord["X"],coord["Y"],coord["Z"])
    a2,b2,c2=transform(position["X"],position["Y"],position["Z"])                                                     
    virtual_d=math.sqrt((a1-a2)**2+(b1-b2)**2+(c1-c2)**2)
    fnew=f*1.0
    if d!=0:
        fnew=f*virtual_d/d

    position['X']=a2
    position['Y']=b2
    position['Z']=c2
    position['F']=fnew
    coord=position1
    return position
#print testcode(0,0,0)


def distance(start, end):
    try:
        x1,y1,z1=start['X'],start['Y'],start['Z']
        x2,y2,z2=end['X'],end['Y'],end['Z']
        return math.sqrt((x1-x2)**2+(y1-y2)**2+(z1-z2)**2)
    except:
        return 0
#print testcode(0,0,0)


def interpolate(start, end, i, n):
    x1,y1,z1,e1=start['X'],start['Y'],start['Z'],start['E']
    x2,y2,z2,e2=end['X'],end['Y'],end['Z'],end['E']
    middle={}
    for c in end:
        if c in end and c in start and c in "XYZE":
            middle[c]=(i*end[c]+(n-i)*start[c])/float(n)
        else:
            middle[c]=end[c]
    return middle


def segmentize(start,end,maxLength):
    l=distance(start,end)
    if l<=maxLength:
        return [end]
    else:
        output=[]
        n=int(math.ceil(l/maxLength))
        for i in range(1,n+1):
            output.append(interpolate(start,end,i,n))
        return output
            
    

f=file(raw_input("Input File: "))
coord={"X":0,"Y":0,"Z":0, "E":0, "F":0}
prefixes="MGXYZESF"
commands="MG"
f2=file(raw_input("Output File: "),"w")
f2.write("G92 X0 Y0 Z0 E0\n")
program=[]
move_count=0
for line in f:
    line=line.strip()
    chunks=line.split(";")[0].split(" ")
    stuff={}
    for chunk in chunks:
        if len(chunk)>1:
            stuff[chunk[0]]=chunk[1:]
            try:
                stuff[chunk[0]]=int(stuff[chunk[0]])
            except:
                try:
                    stuff[chunk[0]]=float(stuff[chunk[0]])
                except:
                    pass
        if "X" in stuff or "Y" in stuff or "Z" in stuff:
            move_count+=1
            for c in coord:
                if c not in stuff:
                    stuff[c]=coord[c]           
    if move_count<=3 and len(stuff)>0:
        program+=[stuff]
    elif len(stuff)>0:
        segments=segmentize(coord,stuff,1)
        program+=segments
    for c in coord:
        if c in stuff:
            coord[c]=stuff[c]
for i in range(len(program)):
    line=program[i]
    if i%100==0:
        print str(i*100.0/len(program))+"%"
    abcline=getABC(line)
    for letter in prefixes:
        if letter in abcline and letter in commands:
            f2.write(letter+str(abcline[letter])+" ")
        elif letter in abcline:
            f2.write(letter+str(round(abcline[letter],3))+" ")
    f2.write("\n")



f2.close()
print "done"




########NEW FILE########
__FILENAME__ = rename
import glob,os

files=glob.glob("*")
print files
for f in files:
    os.rename(f,f.replace(".ipt",""))

########NEW FILE########
