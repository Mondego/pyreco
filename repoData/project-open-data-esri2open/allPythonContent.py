__FILENAME__ = esri2open
# ---------------------------------------------------------------------------
# esri2open.py
# Created on: March 11, 2013
# Created by: Michael Byrne
# Federal Communications Commission
# exports the feature classes for any feature class to
# a csv file, JSON file or geoJSON file 
# also adding edits from sgillies, Shaun Walbridge, and Calvin Metcalf
# updates include using the python json.dumps method and indentation issues
# merge of Calvin's esri2geo and export to sqlite
# last edits made 7/26/2013
# ---------------------------------------------------------------------------
#imports
from arcpy import AddMessage, GetCount_management
from utilities import getExt
from parseRow import parse
from prepare import prepareFile

#----
#close file
#----
def closeJSON(out):
    out.write("""]}""")
    out.close()
    return True
    
def closeSqlite(out):
    out[2].commit()
    out[1].close()
    return True
    
def closeCSV(out):
    out[1].close()
    return True

def closeUp(out,fileType):
    if fileType == "geojson":    
        return closeJSON(out)
    elif fileType == "csv":    
        return closeCSV(out)
    if fileType == "json":    
        return closeJSON(out)
    else:
        return False

#this is the meat of the function, we could put it into a seperate file if we wanted
def writeFile(outArray,featureClass,fileType,includeGeometry, first=True):
    parser = parse(outArray,featureClass,fileType,includeGeometry,first)
    #wrap it in a try so we don't lock the database
    try:
        for row in parser.rows:
            #parse row
            parser.parse(row)
    except Exception as e:
        #using chrome has rubbed off on me
        AddMessage("OH SNAP! " + str(e))
    finally:
        #clean up
        return parser.cleanUp(row)

#this is the main entry point into the module
def toOpen(featureClass, outJSON, includeGeometry="geojson"):
    #check the file type based on the extention
    fileType=getExt(outJSON)
    #some sanity checking
    #valid geojson needs features, seriously you'll get an error
    if not int(GetCount_management(featureClass).getOutput(0)):
        AddMessage("No features found, skipping")
        return
    elif not fileType:
        AddMessage("this filetype doesn't make sense")
        return
    #geojson needs geometry
    if fileType=="geojson":
        includeGeometry="geojson"
    elif fileType=="sqlite":
        includeGeometry="well known binary"
    else:
        includeGeometry=includeGeometry.lower()
    #open up the file
    outFile=prepareFile(outJSON,featureClass,fileType,includeGeometry)
    #outFile will be false if the format isn't defined
    if not outFile:
        AddMessage("I don't understand the format")
        return
    #write the rows
    writeFile(outFile,featureClass,fileType,includeGeometry)
    #go home
    closeUp(outFile,fileType)

########NEW FILE########
__FILENAME__ = parseGeometry
from wkt import getWKTFunc
from wkb import getWKBFunc

def getPoint(pt):
    return [pt.X,pt.Y]
def parseLineGeom(line):
    out=[]
    lineCount=line.count
    if lineCount ==1:
        return ["Point",getPoint(line[0])]
    i=0
    while i<lineCount:
        pt=line[i]
        out.append(getPoint(pt))
        i+=1
    if len(out)==2 and out[0]==out[1]:
        return ["Point",out[0]]
    return ["LineString",out]
def parsePolyGeom(poly):
    out=[]
    polyCount=poly.count
    i=0
    polys=[]
    while i<polyCount:
        pt=poly[i]
        if pt:
            out.append(getPoint(pt))
        else:
            polys.append(out)
            out=[]
        i+=1
    polys.append(out)
    if len(polys[0])==3:
        return ["LineString", polys[0][:2]]
    if len(polys[0])<3:
        return ["Point",polys[0][0]]
    return ["Polygon",polys]
def parsePoint(geometry):
    geo=dict()
    geo["type"]="Point"
    geo["coordinates"]=getPoint(geometry.firstPoint)
    return geo
def parseMultiPoint(geometry):
    if not geometry.partCount:
        return {}
    elif geometry.pointCount == 1:
        return parsePoint(geometry)
    else:
        geo=dict()
        geo["type"]="MultiPoint"
        points=[]
        pointCount=geometry.pointCount
        i=0
        while i<pointCount:
            point=geometry.getPart(i)
            points.append(getPoint(point))
            i+=1
        geo["coordinates"]=points
        return geo
def parseLineString(geometry):
    if not geometry.partCount:
        return {}
    geo=dict()
    outLine=parseLineGeom(geometry.getPart(0))
    geo["type"]=outLine[0]
    geo["coordinates"]=outLine[1]
    return geo
def parseMultiLineString(geometry):
    if not geometry.partCount:
        return {}
    elif geometry.partCount==1:
        return parseLineString(geometry)
    else:
        lineGeo=dict()
        points=[]
        lines=[]
        lineCount=geometry.partCount
        i=0
        while i<lineCount:
            outLine = parseLineGeom(geometry.getPart(i))
            if outLine[0]=="LineString":
                lines.append(outLine[1])
            elif outLine[1]=="Point":
                points.append(outLine[1])
            i+=1
        if lines:
            if len(lines)==1:
                lineGeo["type"]="LineString"
                lineGeo["coordinates"]=lines[0]
            else:
                lineGeo["type"]="MultiLineString"
                lineGeo["coordinates"]=lines
        if points:
            pointGeo={}
            pointGeo["coordinates"]=points
            if len(pointGeo["coordinates"])==1:
                pointGeo["coordinates"]=pointGeo["coordinates"][0]
                pointGeo["type"]="Point"
            else:
                pointGeo["type"]="MultiPoint"
        if lines and not points:
            return lineGeo
        elif points and not lines:
            return pointGeo
        elif points and lines:
            out = {}
            out["type"]="GeometryCollection"
            out["geometries"] = [pointGeo,lineGeo]
            return out
        else:
            return {}
def parsePolygon(geometry):
    if not geometry.partCount:
        return {}
    geo={}
    outPoly = parsePolyGeom(geometry.getPart(0))
    geo["type"]=outPoly[0]
    geo["coordinates"]=outPoly[1]
    return geo
def parseMultiPolygon(geometry):
    if not geometry.partCount:
        return {}
    elif geometry.partCount==1:
        return parsePolygon(geometry)
    else:
        polys=[]
        lines=[]
        points=[]
        polyCount=geometry.partCount
        i=0
        while i<polyCount:
            polyPart = parsePolyGeom(geometry.getPart(i))
            if polyPart[0]=="Polygon":
                polys.append(polyPart[1])
            elif polyPart[0]=="Point":
                points.append(polyPart[1])
            elif polyPart[0]=="LineString":
                lines.append(polyPart[1])
            i+=1
        num = 0
        if polys:
            polyGeo={}
            num+=1
            polyGeo["coordinates"]=polys
            if len(polyGeo["coordinates"])==1:
                polyGeo["coordinates"]=polyGeo["coordinates"][0]
                polyGeo["type"]="Polygon"
            else:
                polyGeo["type"]="MultiPolygon"
        if points:
            num+=1
            pointGeo={}
            pointGeo["coordinates"]=points
            if len(pointGeo["coordinates"])==1:
                pointGeo["coordinates"]=pointGeo["coordinates"][0]
                pointGeo["type"]="Point"
            else:
                pointGeo["type"]="MultiPoint"
        if lines:
            num+=1
            lineGeo={}
            lineGeo["coordinates"]=lineGeo
            if len(lineGeo["coordinates"])==1:
                lineGeo["coordinates"]=lineGeo["coordinates"][0]
                pointGeo["type"]="LineString"
            else:
                pointGeo["type"]="MultiLineString"
        if polys and not points and not lines:
            return polyGeo
        elif points and not polys and not lines:
            return pointGeo
        elif lines and not polys and not points:
            return lineGeo
        elif num>1:
            out = {}
            out["type"]="GeometryCollection"
            outGeo = []
            if polys:
                outGeo.append(polyGeo)
            if points:
                outGeo.append(pointGeo)
            if lines:
                outGeo.append(lineGeo)
            out["geometries"]=outGeo
            return out
        else:
            return {}
def parseMultiPatch():
    #noop at the moment
    return {}

#this should probobly be a class
def getParseFunc(shpType, geo):
    if geo == "none":
        return False
    elif geo=="well known binary":
        return getWKBFunc(shpType)
    else:
        if shpType == "point":
            fun = parsePoint
        elif shpType == "multipoint":
            fun = parseMultiPoint
        elif shpType == "polyline":
            fun = parseMultiLineString
        elif shpType == "polygon":
            fun = parseMultiPolygon
        else:
            fun = parseMultiPatch
    if geo=="geojson":
        return fun
    elif geo=="well known text":
        return getWKTFunc(fun)
########NEW FILE########
__FILENAME__ = parseRow
from utilities import listFields, getShp, getOID, statusMessage, parseProp, makeInter
from arcpy import SpatialReference, SearchCursor  
from parseGeometry import getParseFunc
from json import dump

#really the only global
wgs84="GEOGCS['GCS_WGS_1984',DATUM['D_WGS_1984',SPHEROID['WGS_1984',6378137.0,298.257223563]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]];-400 -400 1000000000;-100000 10000;-100000 10000;8.98315284119522E-09;0.001;0.001;IsHighPrecision"

class parse:
    def __init__(self,outFile,featureClass,fileType,includeGeometry, first=True):
        self.outFile = outFile
        self.fileType = fileType
        #first we set put the local variables we'll need
        [self.shp,self.shpType]=getShp(featureClass)
        self.fields=listFields(featureClass)
        self.oid=getOID(self.fields)
        sr=SpatialReference()
        sr.loadFromString(wgs84)
        #the search cursor
        self.rows=SearchCursor(featureClass,"",sr)
        #don't want the shape field showing up as a property
        del self.fields[self.shp]
        self.first=first
        self.status = statusMessage(featureClass)
        #define the correct geometry function if we're exporting geometry
        self.parseGeo = getParseFunc(self.shpType,includeGeometry)
        self.i=0
        if fileType=="geojson":    
            self.parse = self.parseGeoJSON
        elif fileType=="csv":    
            self.parse = self.parseCSV
        elif fileType=="json":    
            self.parse = self.parseJSON
        elif fileType=="sqlite":    
            self.parse = self.parseSqlite

    def cleanUp(self,row):
        del row
        del self.rows
        return True

    def parseCSV(self,row):
        #more messages
        self.status.update()
        fc=parseProp(row,self.fields, self.shp)
        if self.parseGeo:
            try:
                fc["geometry"]=self.parseGeo(row.getValue(self.shp))
            except:
                return
        self.outFile[0].writerow(fc)

    def parseGeoJSON(self,row):
        #more messages
        self.status.update()
        fc={"type": "Feature"}
        if self.parseGeo:
            try:
                fc["geometry"]=self.parseGeo(row.getValue(self.shp))
            except:
                return
        else:
            raise NameError("we need geometry for geojson")
        fc["id"]=row.getValue(self.oid)
        fc["properties"]=parseProp(row,self.fields, self.shp)
        if fc["geometry"]=={}:
            return
        if self.first:
            self.first=False
            dump(fc,self.outFile)
        else:
            #if it isn't the first feature, add a comma
            self.outFile.write(",")
            dump(fc,self.outFile)

    def parseJSON(self,row):
        #more messages
        self.status.update()
        fc=parseProp(row,self.fields, self.shp)
        if self.parseGeo:
            try:
                fc["geometry"]=self.parseGeo(row.getValue(self.shp))
            except:
                return
        if self.first:
            self.first=False
            dump(fc,self.outFile)
        else:
            self.outFile.write(",")
            dump(fc,self.outFile)

    def parseSqlite(self,row):
        #more messages
        self.status.update()
        fc=parseProp(row,self.fields, self.shp)
        self.i=self.i+1
        fc["OGC_FID"]=self.i
        if self.parseGeo:
            try:
                fc["GEOMETRY"]=self.parseGeo(row.getValue(self.shp))
            except:
                return
        keys = fc.keys()
        values = fc.values()
        [name,c,conn]=self.outFile
        c.execute("""insert into {0}({1})
                values({2})
                """.format(name,", ".join(keys),makeInter(len(values))),values)
        conn.commit()
########NEW FILE########
__FILENAME__ = prepare
from csv import DictWriter
from utilities import listFields,getShp, parseFieldType
from sqlite3 import Connection
from os.path import splitext, split

def prepareCSV(outJSON,featureClass,fileType,includeGeometry):
    shp=getShp(featureClass)[0]
    fields=listFields(featureClass)
    fieldNames = []
    out = open(outJSON,"wb")
    for field in fields:
        if (fields[field] != u'OID') and field.lower() !=shp.lower():
            fieldNames.append(field)
    if includeGeometry!="none":
        fieldNames.append("geometry")
    outCSV=DictWriter(out,fieldNames,extrasaction='ignore')
    fieldObject = {}
    for fieldName in fieldNames:
        fieldObject[fieldName]=fieldName
    outCSV.writerow(fieldObject)
    return [outCSV,out]
    
def prepareSqlite(out,featureClass,fileType,includeGeometry):
    [shp,shpType]=getShp(featureClass)
    if shpType == "point":
        gType = 1
    elif shpType == "multipoint":
        gType = 4
    elif shpType == "polyline":
        gType = 5
    elif shpType == "polygon":
        gType = 6
    fields=listFields(featureClass)
    fieldNames = []
    fieldNames.append("OGC_FID INTEGER PRIMARY KEY")
    if includeGeometry:
        fieldNames.append("GEOMETRY blob")
    for field in fields:
        if (fields[field] != u'OID') and field.lower() !=shp.lower():
            fieldNames.append(parseFieldType(field,fields[field]))

    conn=Connection(out)
    c=conn.cursor()
    name = splitext(split(out)[1])[0]
    c.execute("""CREATE TABLE geometry_columns (     f_table_name VARCHAR,      f_geometry_column VARCHAR,      geometry_type INTEGER,      coord_dimension INTEGER,      srid INTEGER,     geometry_format VARCHAR )""")
    c.execute("""insert into geometry_columns( f_table_name, f_geometry_column, geometry_type, coord_dimension, srid, geometry_format) values(?,?,?,?,?,?)""",(name,"GEOMETRY",gType,2,4326,"WKB"))
    c.execute("""CREATE TABLE spatial_ref_sys        (     srid INTEGER UNIQUE,     auth_name TEXT,     auth_srid TEXT,     srtext TEXT)""")
    c.execute("insert into spatial_ref_sys(srid ,auth_name ,auth_srid ,srtext) values(?,?,?,?)",(4326, u'EPSG', 4326, u'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]'))
    c.execute("create table {0}({1})".format(name,", ".join(fieldNames)))
    return [name,c,conn]
def prepareGeoJSON(outJSON,*args):
    out = open(outJSON,"wb")
    out.write("""{"type":"FeatureCollection","features":[""")
    return out
    
def prepareJSON(outJSON,*args):
    out = open(outJSON,"wb")
    out.write("""{"docs":[""")
    return out

def prepareFile(outJSON,featureClass,fileType,includeGeometry):
    if fileType == "geojson":    
        return prepareGeoJSON(outJSON,featureClass,fileType,includeGeometry)
    elif fileType == "csv":    
        return prepareCSV(outJSON,featureClass,fileType,includeGeometry)
    elif fileType == "json":    
        return prepareJSON(outJSON,featureClass,fileType,includeGeometry)
    elif fileType == "sqlite": 
        return prepareSqlite(outJSON,featureClass,fileType,includeGeometry)
    else:
        return False
########NEW FILE########
__FILENAME__ = utilities
from arcpy import ListFields,Describe,SetProgressorLabel,SetProgressorPosition,GetCount_management, SetProgressor, AddMessage
from os.path import splitext

#utility functions we will call more then once

#takes the input feature class and returns a dict with 
#	the field name as key and field types as values
def listFields(featureClass):
    fields=ListFields(featureClass)
    out=dict()
    for fld in fields:
        if (fld.name.lower() not in ('shape_length','shape_area','shape.len','shape.length','shape_len','shape.area') and fld.name.find(".")==-1):
            out[fld.name]=fld.type
    return out

#takes the input geometry object and returns
#	a list of [name of shape field, name of shape type]
def getShp(shp):
    desc = Describe(shp)
    return [desc.ShapeFieldName,desc.shapeType.lower()]
    
#takes the fields object from above, tells you which is the OID 
def getOID(fields):
    for key, value in fields.items():
        if value== u'OID':
            return key
            
#for putting a % based status total up
class statusMessage:
    def __init__(self,featureClass):
        self.featureCount = int(GetCount_management(featureClass).getOutput(0))
        SetProgressor("step", "Found {0} features".format(str(self.featureCount)), 0, 100,1)
        AddMessage("Found "+str(self.featureCount)+" features")
        self.percent = 0
        self.current=0
    def update(self):
        self.current+=1
        newPercent = int((self.current*100)/self.featureCount)
        if newPercent != self.percent:
            self.percent=newPercent
            SetProgressorLabel("{0}% done".format(str(self.percent)))
            SetProgressorPosition(self.percent)

#parse the properties, get rid of ones we don't want, i.e. null, or the shape
def parseProp(row,fields, shp):
    out=dict()
    for field in fields:
        if (fields[field] != u'OID') and field.lower() not in ('shape_length','shape_area','shape.len','shape.length','shape_len','shape.area',shp.lower()) and row.getValue(field) is not None:
            if fields[field] == "Date":
                value = str(row.getValue(field).date())
            elif fields[field] == "String":
                value = row.getValue(field).strip()
            else:
                value = row.getValue(field)
            if value != "":
                out[field]=value
    return out

def getExt(fileName):
    split=splitext(fileName)
    if split[1]:
        return split[1][1:].lower()
    else:
        return False

def parseFieldType(name, esriType):
    if esriType.lower() in ("text","string","date"):
        return name+" text"
    elif esriType.lower() in ("short","long","integer"):
        return name+" integer"
    elif esriType.lower() in ("float","single","double"):
        return name+" real"
    else:
        return name+" blob"

def zm(shp):
    desc = Describe(shp)
    return [desc.hasZ,desc.hasM]

def makeInter(n):
    out = []
    i = 0
    while i<n:
        i+=1
        out.append("?")
    return ",".join(out)
########NEW FILE########
__FILENAME__ = wkb
from struct import pack
from sqlite3 import Binary
def pts(c):
    return ["dd",[c.X,c.Y]]
def pt4mp(c):
    return ["Bidd",[1,1,c.X,c.Y]]
def mp(coordinates):
    partCount=coordinates.partCount
    i=0
    out = ["I",[0]]
    while i<partCount:
        pt = coordinates.getPart(i)
        [ptrn,c]=pt4mp(pt)
        out[0]+=ptrn
        out[1][0]+=1
        out[1].extend(c)
        i+=1
    return out
def lineSt(coordinates):
    partCount=coordinates.count
    i=0
    out = ["I",[0]]
    while i<partCount:
        pt = coordinates[i]
        [ptrn,c]=pts(pt)
        out[0]+=ptrn
        out[1][0]+=1
        out[1].extend(c)
        i+=1
    return out
def multiLine(coordinates):
    partCount=coordinates.partCount
    i=0
    out = ["I",[0]]
    while i<partCount:
        part = coordinates.getPart(i)
        [ptrn,c]=lineSt(part)
        out[0]+="BI"
        out[0]+=ptrn
        out[1][0]+=1
        out[1].extend([1,2])
        out[1].extend(c)
        i+=1
    return out
def linearRing(coordinates):
    partCount=coordinates.count
    i=0
    values =[0]
    outnum = "I"
    out = ["I",[0]]
    while i<partCount:
        pt = coordinates[i]
        if pt:
            [ptrn,c]=pts(pt)
            outnum+=ptrn
            values[0]+=1
            values.extend(c)
        else:
            if values[0]<4:
                return False
            out[0]+=outnum
            out[1][0]+=1
            out[1].extend(values)
            values =[0]
            outnum = "I"
        i+=1
    if values[0]<4:
        return False 
    out[0]+=outnum
    out[1][0]+=1
    out[1].extend(values)
    return out
def multiRing(coordinates):
    partCount=coordinates.partCount
    i=0
    out = ["I",[0]]
    while i<partCount:
        part = coordinates.getPart(i)
        [ptrn,c]=linearRing(part)
        out[0]+="BI"
        out[0]+=ptrn
        out[1][0]+=1
        out[1].extend([1,3])
        out[1].extend(c)
        i+=1
    return out
    return out
def makePoint(c):
    values = ["<BI",1,1]
    [ptrn,coords] = pts(c.getPart(0))
    values[0]+=ptrn
    values.extend(coords)
    return Binary(pack(*values))
def makeMultiPoint(c):
    values = ["<BI",1,4]
    [ptrn,coords]=mp(c)
    values[0]+=ptrn
    values.extend(coords)
    return Binary(pack(*values))
def makeMultiLineString(c):
    if c.partCount==1:
        values = ["<BI",1,2]
        [ptrn,coords]=lineSt(c.getPart(0))
    elif c.partCount>1:
        values = ["<BI",1,5]
        [ptrn,coords]=multiLine(c)
    else:
        return False
    values[0]+=ptrn
    values.extend(coords)
    return Binary(pack(*values))
def makeMultiPolygon(c):
    if c.partCount==1:
        values = ["<BI",1,3]
        [ptrn,coords]=linearRing(c.getPart(0))
    elif c.partCount>1:
        values = ["<BI",1,6]
        [ptrn,coords]=multiRing(c)
    else:
        return False
    values[0]+=ptrn
    values.extend(coords)
    return Binary(pack(*values))

def getWKBFunc(type):
    if type == "point":
        return makePoint
    elif type == "multipoint":
        return makeMultiPoint
    elif type == "polyline":
        return makeMultiLineString
    elif type == "polygon":
        return makeMultiPolygon

########NEW FILE########
__FILENAME__ = wkt
def point(c):
    return "{0} {1}".format(c[0],c[1])
def multiPoint(coordinates):
    values =[]
    for coord in coordinates:
        values.append("({0})".format(point(coord)))
    return ", ".join(values)
def linearRing(coordinates):
    values =[]
    for coord in coordinates:
        values.append(point(coord))
    return ", ".join(values)
def multiRing(coordinates):
    values =[]
    for lineString in coordinates:
        values.append("({0})".format(linearRing(lineString)))
    return ", ".join(values)
def metaMultiRing(coordinates):
    values =[]
    for lineString in coordinates:
        values.append("({0})".format(multiRing(lineString)))
    return ", ".join(values)
def makePoint(c):
    return ["Point",point(c)]
def makeMultiPoint(c):
    return ["MultiPoint",multiPoint(c)]
def makeLineString(c):
    return ["LineString",linearRing(c)]
def makeMultiLineString(c):
    return ["MultiLineString",multiRing(c)]
def makePolygon(c):
    return ["Polygon",multiRing(c)]
def makeMultiPolygon(c):
    return ["MultiPolygon",metaMultiRing(c)]
def makeCollection(geometries):
    values = []
    for geom in geometries:
        [ptrn,coords]=parseGeo(geom)
        values.append("{0} ({1})".format(ptrn,coords))
    return ["GeomCollection",", ".join(values)]
def parseGeo(geometry):
    if geometry["type"]=="Point":
        return makePoint(geometry["coordinates"])
    elif geometry["type"]=="MultiPoint":
        return makeMultiPoint(geometry["coordinates"])
    elif geometry["type"]=="LineString":
        return makeLineString(geometry["coordinates"])
    elif geometry["type"]=="MultiLineString":
        return makeMultiLineString(geometry["coordinates"])
    elif geometry["type"]=="Polygon":
        return makePolygon(geometry["coordinates"])
    elif geometry["type"]=="MultiPolygon":
        return makeMultiPolygon(geometry["coordinates"])
    elif geometry["type"]=="GeometryCollection":
        return makeCollection(geometry["geometries"])

def makeWKT(geometry):
    [ptrn,coords]=parseGeo(geometry)
    return "{0} ({1})".format(ptrn,coords)

def getWKTFunc(fun):
    return lambda x: makeWKT(fun(x))
    
########NEW FILE########
__FILENAME__ = esriopenaddin_addin
from os.path import dirname,join
from sys.path import insert
from pythonaddins import GPToolDialog

# enable local imports
local_path = dirname(__file__)
insert(0, local_path)

# get the path for our TBX
toolbox = join(local_path, "esri2open.tbx")

class OpenStandard(object):
    """Implementation for esriopen_standard.button (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
    def onClick(self):
        GPToolDialog(toolbox, 'esri2open')

class OpenMerge(object):
    """Implementation for esriopen_merge.button (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
    def onClick(self):
        GPToolDialog(toolbox, 'esri2openMerge')

class OpenMultiple(object):
    """Implementation for esriopen_multiple.button (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
    def onClick(self):
        GPToolDialog(toolbox, 'esri2openMulti')

########NEW FILE########
__FILENAME__ = merge
from arcpy import GetParameterAsText
from esri2open import writeFile, prepareGeoJSON, closeJSON
#compute the peramaters
features = GetParameterAsText(0).split(";")
outJSON=GetParameterAsText(1)
includeGeometry = "geojson"
fileType = "geojson"
out=prepareGeoJSON(outJSON)
first=True#this makes sure sure we arn't missing commas
for feature in features:
    if feature[0] in ("'",'"'):
        feature = feature[1:-1]
    writeFile(out,feature,fileType,includeGeometry, first)
    first=False
closeJSON(out)
########NEW FILE########
__FILENAME__ = multiple
from arcpy import GetParameterAsText, AddMessage
from esri2open import toOpen
from os import path, sep
def getName(feature):
    name = path.splitext(path.split(feature)[1])
    if name[1]:
        if name[1]==".shp":
            return name[0]
        else:
            return name[1][1:]
    else:
        return name[0]
    
features = GetParameterAsText(0).split(";")
outFolder = GetParameterAsText(1)
outType = GetParameterAsText(2)
includeGeometries = ("geojson" if (GetParameterAsText(3)=="Default") else GetParameterAsText(3)).lower()
for feature in features:
    if feature[0] in ("'",'"'):
        feature = feature[1:-1]
    outName = getName(feature)
    outPath = "{0}{1}{2}.{3}".format(outFolder,sep,outName,outType)
    if path.exists(outPath):
        AddMessage("{0} exists, skipping".format(outName))
        continue
    AddMessage("starting {0}".format(outName))
    toOpen(feature,outPath,includeGeometries)
########NEW FILE########
__FILENAME__ = single
from arcpy import GetParameterAsText
from esri2open import toOpen
toOpen(GetParameterAsText(0),GetParameterAsText(1),("geojson" if (GetParameterAsText(2)=="Default") else GetParameterAsText(2)))
########NEW FILE########
__FILENAME__ = makeaddin
import os
import re
import zipfile

current_path = os.path.dirname(os.path.abspath(__file__))

out_zip_name = os.path.join(current_path, 
                            os.path.basename(current_path) + ".esriaddin")

BACKUP_FILE_PATTERN = re.compile(".*_addin_[0-9]+[.]py$", re.IGNORECASE)

def looks_like_a_backup(filename):
    return bool(BACKUP_FILE_PATTERN.match(filename))

zip_file = zipfile.ZipFile(out_zip_name, 'w')
for filename in ('config.xml', 'README.md', 'makeaddin.py'):
    zip_file.write(os.path.join(current_path, filename), filename)
dirs_to_add = ['Images', 'Install']
for directory in dirs_to_add:
    for (path, dirs, files) in os.walk(os.path.join(current_path, directory)):
        archive_path = os.path.relpath(path, current_path)
        found_file = False
        for file in (f for f in files if not looks_like_a_backup(f)):
            archive_file = os.path.join(archive_path, file)
            print archive_file
            zip_file.write(os.path.join(path, file), archive_file)
            found_file = True
        if not found_file:
            zip_file.writestr(os.path.join(archive_path, 'placeholder.txt'), 
                              "(Empty directory)")
zip_file.close()

########NEW FILE########
