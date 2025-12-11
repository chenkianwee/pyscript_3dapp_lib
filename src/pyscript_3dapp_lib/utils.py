import io
import csv
import geomie3d
import numpy as np
from stl import mesh
from plyfile import PlyData, PlyElement

from pyscript import document
from js import Uint8Array, File, URL

def convertxyz2zxy(xyzs: np.ndarray) -> np.ndarray:
    """
    convert xyzs from xyz cs to zxy coordinates

    Parameters
    ----------
    xyzs : np.ndarray
        np.ndarray[shape(npoints, 3)] 

    Returns
    -------
    np.ndarray
        np.ndarray[shape(npoints, 3)]
    """
    orig_cs = geomie3d.utility.CoordinateSystem([0,0,0], [1,0,0], [0,1,0])
    dest_cs = geomie3d.utility.CoordinateSystem([0,0,0], [0,0,1], [1,0,0])
    trsf_mat = geomie3d.calculate.cs2cs_matrice(orig_cs, dest_cs)
    trsf_xyzs = geomie3d.calculate.trsf_xyzs(xyzs, trsf_mat)
    return trsf_xyzs

def read_csv_web(grid_bytes: bytes) -> list:
    """
    read csv file for webapp

    Parameters
    ----------
    grid_bytes: bytes
        JS bytes from the file specified. Need to be converted to python with .to_py() function.

    Returns
    -------
    list
        A dictionary containing:
            - "xyzs": np.ndarray[(n_triangles, 3, 3)].
    """
    grid_bytes = grid_bytes.to_py()
    grid_bstream = io.BytesIO(grid_bytes)
    text_buffer = io.TextIOWrapper(grid_bstream, encoding='utf-8')
    reader = csv.reader(text_buffer)
    rows = list(reader)
    return rows

def read_stl_web(stl_bytes: bytes) -> dict:
    """
    read stl file for webapp

    Parameters
    ----------
    stl_bytes: bytes
        JS bytes from the file specified. Need to be converted to python with .to_py() function.

    Returns
    -------
    dict
        A dictionary containing:
            - "xyzs": np.ndarray[(n_triangles, 3, 3)].
    """
    stl_bytes = stl_bytes.to_py()
    stl_bstream = io.BytesIO(stl_bytes)
    stl_mesh = mesh.Mesh.from_file('', fh=stl_bstream)
    mesh_data = stl_mesh.vectors
    return {'xyzs': mesh_data}

def read_ply_web(ply_bytes: bytes) -> dict:
    """
    read ply file for webapp

    Parameters
    ----------
    ply_bytes: bytes
        JS bytes from the file specified. Need to be converted to python with .to_py() function.

    Returns
    -------
    np.ndarray
        np.ndarray[(n_points, n_attributes)]
    """
    ply_bytes = ply_bytes.to_py()
    bstream = io.BytesIO(ply_bytes)
    plydata = PlyData.read(bstream)
    data = plydata['vertex'].data
    data = list(map(list, data))
    data = np.array(data)
    return data

def write_ply_web(vertex_data: list[tuple], dtype_val: list[tuple]) -> io.BytesIO:
    """
    write ply file for webapp

    Parameters
    ----------
    vertex_data: list[tuple]
        list[shape(npts, 3)]

    dtype_val: list[tuple]
        example of dtype_val = [('x', 'f4'), ('y', 'f4'), ('z', 'f4'), ('temperature', 'f4')]

    Returns
    -------
    io.BytesIO
        bufferstream to be written to file in the create_hidden_link function 
    """
    ply_vertex_data = np.array(vertex_data, dtype=dtype_val)
    element = PlyElement.describe(ply_vertex_data, 'vertex')
    ply = PlyData([element], text=True)

    # Write to BytesIO
    buffer = io.BytesIO()
    ply.write(buffer)
    return buffer

def write_csv_web(rows: list[list]) -> io.BytesIO:
    """
    write csv file for webapp

    Parameters
    ----------
    rows: list[list]
        rows to write to csv

    Returns
    -------
    io.BytesIO
        bufferstream to be written to file in the create_hidden_link function 
    """
    # Create a bytes buffer
    buffer = io.BytesIO()
    # Wrap it in a text wrapper for the csv module
    text_buffer = io.TextIOWrapper(buffer, encoding='utf-8', newline='')
    writer = csv.writer(text_buffer)
    writer.writerows(rows)
    text_buffer.flush()
    text_buffer.detach()
    return buffer

def create_hidden_link(bstream: io.BytesIO, file_name: str, file_type: str):
    """
    download file from the webapp

    Parameters
    ----------
    bstream: io.BytesIO
        the data to write to file

    file_name: str
        the name of the file to write to and download

    file_type: str
        the extension of the file.

    """
    buffer = bstream.getbuffer()
    nbuffer = len(buffer)
    js_array = Uint8Array.new(nbuffer)
    js_array.assign(buffer)

    file = File.new([js_array], file_name, {type: f"application/{file_type}"})
    url = URL.createObjectURL(file)

    hidden_link = document.createElement("a")
    hidden_link.setAttribute("download", f"{file_name}.{file_type}")
    hidden_link.setAttribute("href", url)
    hidden_link.click()

async def get_bytes_from_file(item) -> bytes:
    """
    read the file item specified by the user.

    Parameters
    ----------
    item: list[tuple]
        list[shape(npts, 3)]

    Returns
    -------
    bytes
        bufferstream to be written to file in the create_hidden_link function 
    """
    array_buf = await item.arrayBuffer()
    return array_buf.to_bytes()

def rgb_falsecolors(vals: list[float], minval: float, mxval: float) -> list:
    """
    generate falsecolor values corresponding to the parameters.

    Parameters
    ----------
    vals: list[float]
        list[shape(n)], values to be converted to rgb of falsecolor.
    
    minval: float
        min val on the falsecolor bar.
        
    mxval: float
        max val on the falsecolor bar.

    Returns
    -------
    list
        list[shape(nvals*3)] list of flat rgb colors. 
    """
    rgbs = geomie3d.utility.calc_falsecolour(vals, minval, mxval)
    rgbs_flat = np.array(rgbs).flatten().tolist()
    return rgbs_flat

def get_cam_place_from_xyzs(xyzs: list[list[float]], zoom_out_val: float = 0.0) -> list[list[float]]:
    """
    calculate placement and look at xyz of the camera

    Parameters
    ----------
    xyzs : list[list[float]]
        list[shape(npts, 3)] the points use to calculate the bounding box.

    zoom_out_val: float, optional
        the distance to zoom out from the camera position. [camposx + zoom_out_val, camposy + zoom_out_val, camposz + zoom_out_val]

    Returns
    -------
    list[list[float]]
        list[shape(2,3)], first points is the cam position, second point is the look at position.
    """
    bbox = geomie3d.calculate.bbox_frm_xyzs(xyzs)
    bbox_arr = bbox.bbox_arr
    cam_pos = [bbox_arr[3] + zoom_out_val, bbox_arr[4] + zoom_out_val, bbox_arr[5] + zoom_out_val]
    bbox_midpt = geomie3d.calculate.bboxes_centre([bbox])[0].tolist()
    cam_place = [cam_pos, bbox_midpt]
    return cam_place