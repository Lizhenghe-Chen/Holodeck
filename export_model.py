#!/usr/bin/env python
"""
将 OBJathor 的 .pkl.gz 模型文件导出为标准的 .obj 格式
用法:
    python export_model.py --asset_id 0a0a8274693445a6b533dce7f97f747c --output_dir ./exported_models
    python export_model.py --asset_path /path/to/asset.pkl.gz --output_dir ./exported_models
"""
import os
import shutil
from argparse import ArgumentParser
from pathlib import Path
import trimesh
import numpy as np
import compress_pickle


def export_obj(pkl_data, output_path, asset_id):
    """将pkl数据导出为OBJ格式"""
    vertices = pkl_data["vertices"]
    triangles = pkl_data["triangles"]
    normals = pkl_data.get("normals", [])
    uvs = pkl_data.get("uvs", [])

    obj_path = os.path.join(output_path, f"{asset_id}.obj")
    mtl_path = os.path.join(output_path, f"{asset_id}.mtl")

    with open(obj_path, "w") as f:
        # 写入材质库引用
        f.write(f"# Exported from OBJathor\n")
        f.write(f"mtllib {asset_id}.mtl\n\n")

        # 写入顶点
        f.write(f"# Vertices ({len(vertices)})\n")
        for v in vertices:
            f.write(f"v {v['x']} {v['y']} {v['z']}\n")

        # 写入UV坐标
        if uvs:
            f.write(f"\n# Texture coordinates ({len(uvs)})\n")
            for uv in uvs:
                f.write(f"vt {uv['x']} {uv['y']}\n")

        # 写入法线
        if normals:
            f.write(f"\n# Normals ({len(normals)})\n")
            for n in normals:
                f.write(f"vn {n['x']} {n['y']} {n['z']}\n")

        # 写入面（三角形）
        # triangles是平铺的整数列表 [v1, v2, v3, v4, v5, v6, ...]，每3个为一个三角形
        num_faces = len(triangles) // 3
        f.write(f"\n# Faces ({num_faces})\n")
        f.write(f"usemtl {asset_id}_material\n")

        for i in range(0, len(triangles), 3):
            # OBJ索引从1开始，而不是0
            v1 = triangles[i] + 1
            v2 = triangles[i + 1] + 1
            v3 = triangles[i + 2] + 1

            if uvs and normals:
                # 格式: f v1/vt1/vn1 v2/vt2/vn2 v3/vt3/vn3
                f.write(f"f {v1}/{v1}/{v1} {v2}/{v2}/{v2} {v3}/{v3}/{v3}\n")
            elif uvs:
                # 格式: f v1/vt1 v2/vt2 v3/vt3
                f.write(f"f {v1}/{v1} {v2}/{v2} {v3}/{v3}\n")
            elif normals:
                # 格式: f v1//vn1 v2//vn2 v3//vn3
                f.write(f"f {v1}//{v1} {v2}//{v2} {v3}//{v3}\n")
            else:
                # 格式: f v1 v2 v3
                f.write(f"f {v1} {v2} {v3}\n")

    # 创建MTL材质文件
    with open(mtl_path, "w") as f:
        f.write(f"# Material for {asset_id}\n")
        f.write(f"newmtl {asset_id}_material\n")
        f.write(f"Ka 1.0 1.0 1.0\n")  # 环境光
        f.write(f"Kd 1.0 1.0 1.0\n")  # 漫反射
        f.write(f"Ks 0.5 0.5 0.5\n")  # 镜面反射
        f.write(f"Ns 10.0\n")  # 光泽度

        # 添加纹理贴图引用
        if "albedoTexturePath" in pkl_data:
            f.write(f"map_Kd albedo.jpg\n")
        if "normalTexturePath" in pkl_data:
            f.write(f"map_Bump normal.jpg\n")
        if "emissionTexturePath" in pkl_data:
            f.write(f"map_Ke emission.jpg\n")

    return obj_path, mtl_path


def copy_textures(asset_dir, output_path):
    """复制纹理文件"""
    texture_files = ["albedo.jpg", "normal.jpg", "emission.jpg"]
    copied = []

    for texture_file in texture_files:
        src = os.path.join(asset_dir, texture_file)
        if os.path.exists(src):
            dst = os.path.join(output_path, texture_file)
            shutil.copy2(src, dst)
            copied.append(texture_file)

    return copied


def export_asset(asset_path, output_dir):
    """导出单个资产"""
    # 获取资产ID
    asset_id = Path(asset_path).stem.replace(".pkl", "")
    asset_dir = os.path.dirname(asset_path)

    # 创建输出目录
    output_path = os.path.join(output_dir, asset_id)
    os.makedirs(output_path, exist_ok=True)

    # 加载pkl数据
    pkl_data = compress_pickle.load(asset_path)

    # 导出OBJ
    obj_path, mtl_path = export_obj(pkl_data, output_path, asset_id)

    # 复制纹理
    textures = copy_textures(asset_dir, output_path)

    print(f"✓ {asset_id}: {obj_path}")

    return output_path


def batch_export(assets_dir, output_dir, limit=None):
    """批量导出资产"""
    # 查找所有.pkl.gz文件
    pkl_files = []
    for root, dirs, files in os.walk(assets_dir):
        for file in files:
            if file.endswith(".pkl.gz"):
                pkl_files.append(os.path.join(root, file))

    print(f"找到 {len(pkl_files)} 个资产")

    if limit:
        pkl_files = pkl_files[:limit]

    # 批量导出
    success = 0
    for pkl_file in pkl_files:
        try:
            export_asset(pkl_file, output_dir)
            success += 1
        except Exception as e:
            asset_id = Path(pkl_file).stem.replace(".pkl", "")
            print(f"✗ {asset_id}: {e}")

    print(f"完成: {success}/{len(pkl_files)}")


if __name__ == "__main__":
    parser = ArgumentParser(description="将 OBJathor .pkl.gz 模型导出为 .obj 格式")

    parser.add_argument(
        "--asset_id",
        help="资产ID（例如: 0a0a8274693445a6b533dce7f97f747c）",
        default=None,
    )
    parser.add_argument(
        "--asset_path", help="直接指定 .pkl.gz 文件的完整路径", default=None
    )
    parser.add_argument(
        "--assets_dir",
        help="资产根目录（用于批量导出）",
        default="/Volumes/DoggyChen/objathor-assets/2023_09_23/assets",
    )
    parser.add_argument("--output_dir", help="输出目录", default="/Volumes/DoggyChen/GitProjects/Gen Scene 2.0/Assets/export_models")
    parser.add_argument("--batch", help="批量导出所有资产", action="store_true")
    parser.add_argument("--limit", help="批量导出时限制数量", type=int, default=None)

    args = parser.parse_args()

    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)

    if args.batch:
        # 批量导出
        batch_export(args.assets_dir, args.output_dir, args.limit)
    elif args.asset_path:
        # 导出单个资产（通过路径）
        export_asset(args.asset_path, args.output_dir)
    elif args.asset_id:
        # 导出单个资产（通过ID）
        asset_path = os.path.join(
            args.assets_dir, args.asset_id, f"{args.asset_id}.pkl.gz"
        )
        if not os.path.exists(asset_path):
            print(f"错误: 找不到资产文件 {asset_path}")
            exit(1)
        export_asset(asset_path, args.output_dir)
    else:
        print("错误: 请指定 --asset_id、--asset_path 或 --batch")
        parser.print_help()
        exit(1)
