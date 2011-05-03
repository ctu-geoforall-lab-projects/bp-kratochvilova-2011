v.in.ogr dsn=/home/anna/Documents/grassdata/ArcCR500_v12/shapes/vod_tok.shp layer=vod_tok output=vod_tok -o -t
r.in.gdal input=/home/anna/Documents/grassdata/ArcCR500_v12/grids/dem/w001001.adf output=w001001 -o
v.in.ogr dsn=/home/anna/Documents/grassdata/ArcCR500_v12/shapes/vod_pl.shp layer=vod_pl output=vod_pl -o -t
v.in.ogr dsn=/home/anna/Documents/grassdata/ArcCR500_v12/shapes/sidlap.shp layer=sidlap output=sidlap -o -t
r.colors map=w001001@PERMANENT raster=dem_srtm@PERMANENT
v.info map=sidlap@PERMANENT
d.menu
d.rast
db.connect
db.connect -p
db.connect -p -c
db.in.ogr
db.in.ogr dsn=/home/anna/Documents/grassdata/ArcCR500_v12/shapes/vod_tok.dbf
v.in.ogr dsn=/home/anna/Documents/grassdata/ArcCR500_v12/shapes/vrstev.shp layer=vrstev output=vrstev -o -t
v.in.ogr dsn=/home/anna/Documents/grassdata/ArcCR500_v12/shapes/sidlab.shp layer=sidlab output=sidlab -o -t
v.in.ogr dsn=/home/anna/Documents/grassdata/ArcCR500_v12/shapes/silnice.shp layer=silnice output=silnice -o -t
v.in.ogr dsn=/home/anna/Documents/grassdata/ArcCR500_v12/shapes/silnice.shp layer=silnice output=silnice --overwrite -o -t
v.in.ogr dsn=/home/anna/Documents/grassdata/ArcCR500_v12/shapes/zel_trat.shp layer=zel_trat output=zel_trat -o -t
v.in.ogr dsn=/home/anna/Documents/grassdata/ArcCR500_v12/shapes/zel_stan.shp layer=zel_stan output=zel_stan -o -t
r.colors.out map=w001001@PERMANENT rules=/home/anna/Desktop/rules
exit
r.in.gdal input=/home/anna/Documents/grassdata/ArcCR500_v12/images/bar_rel.tif output=bar_rel -o
r.in.gdal input=/home/anna/Documents/grassdata/ArcCR500_v12/images/bar_rel.tif output=bar_rel --overwrite -o
exit
g.gui
exit
nviz elevation=w001001@PERMANENT
r.info -m
r.info -m map=w001001@PERMANENT
g.gui
exit
