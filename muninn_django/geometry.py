import math

from django.contrib.gis.geos import Polygon, LineString, LinearRing, MultiPolygon, MultiLineString, GeometryCollection


def polygon_rotation(pts):
    # return wether polygon is:
    #  1: anti-clockwise rotation (right-hand-rule) -> use inner area
    #  0: no rotation -> polygon is empty or invalid
    # -1: clockwise rotation (left-hand-rule) -> use outer area
    # this can be calculated by determining the signed area of the polygon
    # (summing the outer products of consecutive pts (taking vectors from (0,0) to the pt))
    prev_pt = pts[0]
    sum = 0
    for pt in pts[1:]:
        sum += pt[1] * prev_pt[0] - pt[0] * prev_pt[1]
        prev_pt = pt
    if sum == 0:
        return 0
    return math.copysign(1, sum)


def wrap_geometry(geometry):
    '''
    Convert lines and polygons from a line/polygon on a sphere to one that fits on a 2D lat/lon canvas with
    -90 <= latitude <= 90 and -180 <= longitude <= 180.

    For lines and polygons this requires splitting the lines/polygons at the dateline.
    For polygons this also requires using a special 'unfolding' to make a polygon that covers the North and/or South
    pole to still cover the whole polar region on a flat 2D area.

    Polygons are only converted if they meet the following conditions:
    - use srid 4326 (WGS84)
    - have no exclusion regions

    The special situation where a polygon covers both poles _and_ runs along the dateline will result in a single
    polygon with a wrong rotation. This type of polygon is turned into a geometry with a hole (i.e. outer polygon is
    the full earth bounding box, and the original polygon becomes the exclusion area).
    Input polygons should be properly oriented using the right-hand rule (= anti clockwise) or they may otherwise be
    turned into exclusions by this algorithm.
    '''
    if geometry is None:
        return geometry
    if geometry.srid != 4326:
        return geometry
    if type(geometry) is Polygon:
        if len(geometry) > 1:
            # We don't support conversion of polygons with holes
            return geometry
        # Polygons need to be divided into sub-polys if they cross the dateline
        coords = geometry[0].coords
        lon, lat = coords[0]
        # map lon to [-180, 180]
        lon = lon + 360 if lon < -180 else (lon - 360 if lon > 180 else lon)
        # current_area = {-1: lon < -180, 0: -180 <= lon <= 180, 1: lon >= 180}
        current_area = 0
        prev_lon, prev_lat = lon, lat
        pts = [(lon, lat)]
        pts_set = [pts]
        crossing_lat = []
        for coord in coords[1:]:
            lon, lat = coord
            # map lon to [-180, 180]
            lon = lon + 360 if lon < -180 else (lon - 360 if lon > 180 else lon)
            # rel_lon = lon mapped to [prev_lon - 180, prev_lon + 180]
            rel_lon = lon + 360 if lon < prev_lon - 180 else (lon - 360 if lon > prev_lon + 180 else lon)
            if rel_lon < -180:
                if current_area == -1:
                    # unsupported polygon
                    return geometry
                # crossing the dateline meridian -> split polygon
                mid_lat = lat + ((-180 - rel_lon) / (prev_lon - rel_lon)) * (prev_lat - lat)
                crossing_lat.append(mid_lat)
                pts.append((-180, mid_lat))
                pts = [(180, mid_lat)]
                pts_set.append(pts)
                current_area -= 1
            elif rel_lon > 180:
                if current_area == 1:
                    # unsupported polygon
                    return geometry
                # crossing the dateline meridian -> split polygon
                mid_lat = prev_lat + ((180 - prev_lon) / (rel_lon - prev_lon)) * (lat - prev_lat)
                crossing_lat.append(mid_lat)
                pts.append((180, mid_lat))
                pts = [(-180, mid_lat)]
                pts_set.append(pts)
                current_area += 1
            prev_lon, prev_lat = lon, lat
            pts.append((lon, lat))
        if len(pts_set) == 1:
            assert len(crossing_lat) == 0
            if polygon_rotation(pts) < 0:
                world = LinearRing(((-180, -90), (180, -90), (180, 90), (-180, 90), (-180, -90)))
                return Polygon(world, LinearRing(pts))
            else:
                return Polygon(LinearRing(pts))
        # prepend final pts to first ring
        pts.extend(pts_set[0])
        pts_set[0] = pts
        del pts_set[-1]
        # check if we need to connect via the north pole
        if len(crossing_lat) > 0:
            max_lat = max(crossing_lat)
            max_index = crossing_lat.index(max_lat)
            next_index = max_index + 1 if max_index < len(crossing_lat) - 1 else 0
            if pts_set[max_index][-1][0] > pts_set[next_index][0][0]:
                # connect pts via the north pole
                pts_set[max_index].append((180, 90))
                pts_set[max_index].append((-180, 90))
                if max_index != next_index:
                    pts_set[max_index].extend(pts_set[next_index])
                    pts_set[next_index] = pts_set[max_index]
                    del pts_set[max_index]
                    del crossing_lat[max_index]
        # check if we need to connect via the south pole
        if len(crossing_lat) > 0:
            min_lat = min(crossing_lat)
            min_index = crossing_lat.index(min_lat)
            next_index = min_index + 1 if min_index < len(crossing_lat) - 1 else 0
            if pts_set[min_index][-1][0] < pts_set[next_index][0][0]:
                # connect pts via the south pole
                pts_set[min_index].append((-180, -90))
                pts_set[min_index].append((180, -90))
                if min_index != next_index:
                    pts_set[min_index].extend(pts_set[next_index])
                    pts_set[next_index] = pts_set[min_index]
                    del pts_set[min_index]
                    del crossing_lat[min_index]
        for pts in pts_set:
            # close ring
            pts.append(pts[0])
        if len(pts_set) == 1:
            return Polygon(LinearRing(pts))
        else:
            return MultiPolygon([Polygon(LinearRing(pts)) for pts in pts_set])

    if type(geometry) is LineString:
        # Lines need to be divided into sub-lines if they cross the dateline
        coords = geometry.coords
        lon, lat = coords[0]
        # map lon to [-180, 180]
        lon = lon + 360 if lon < -180 else (lon - 360 if lon > 180 else lon)
        prev_lon, prev_lat = lon, lat
        pts = [(lon, lat)]
        pts_set = [pts]
        for coord in coords[1:]:
            lon, lat = coord
            # map lon to [-180, 180]
            lon = lon + 360 if lon < -180 else (lon - 360 if lon > 180 else lon)
            # rel_lon = lon mapped to [prev_lon - 180, prev_lon + 180]
            rel_lon = lon + 360 if lon < prev_lon - 180 else (lon - 360 if lon > prev_lon + 180 else lon)
            if rel_lon < -180:
                # crossing the dateline meridian -> split line
                mid_lat = lat + ((-180 - rel_lon) / (prev_lon - rel_lon)) * (prev_lat - lat)
                pts.append((-180, mid_lat))
                pts = [(180, mid_lat)]
                pts_set.append(pts)
            elif rel_lon > 180:
                # crossing the dateline meridian -> split line
                mid_lat = prev_lat + ((180 - prev_lon) / (rel_lon - prev_lon)) * (lat - prev_lat)
                pts.append((180, mid_lat))
                pts = [(-180, mid_lat)]
                pts_set.append(pts)
            prev_lon, prev_lat = lon, lat
            pts.append((lon, lat))
        if len(pts_set) > 1:
            return MultiLineString([LineString(pts) for pts in pts_set])
        else:
            return LineString(pts)
    if type(geometry) is MultiPolygon:
        polys = []
        for poly in geometry:
            result = wrap_geometry(poly)
            if type(result) is MultiPolygon:
                polys.extend(result)
            else:
                polys.append(result)
        return MultiPolygon(polys)
    if type(geometry) is MultiLineString:
        lines = []
        for line in geometry:
            result = wrap_geometry(line)
            if type(result) is MultiLineString:
                lines.extend(result)
            else:
                lines.append(result)
        return MultiLineString(lines)
    if type(geometry) is GeometryCollection:
        return GeometryCollection([wrap_geometry(entry) for entry in geometry])
    return geometry
