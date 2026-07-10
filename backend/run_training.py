import json, urllib.request, urllib.error, subprocess

BASE = "http://localhost:8000"

# === Step 1: Insert remote_sensing scene ===
print("=== Insert remote_sensing scene ===")
subprocess.run([
    "docker", "exec", "zqs-postgres", "psql", "-U", "zqs", "-d", "zqs", "-c",
    """INSERT INTO detection_scenes (name, display_name, description, category, class_names, class_names_cn, is_active, created_by)
VALUES ('remote_sensing', '遥感目标检测', '遥感图像目标检测场景，支持飞机、储罐、立交桥、操场等目标检测',
'rsod', '["aircraft", "oiltank", "overpass", "playground"]',
'{"aircraft": "飞机", "oiltank": "储罐", "overpass": "立交桥", "playground": "操场"}', true, 1)
ON CONFLICT (name) DO NOTHING;"""
], check=False)

# === Step 2: Login ===
print("\n=== Login ===")
resp = urllib.request.urlopen(urllib.request.Request(
    f"{BASE}/api/auth/login",
    data=json.dumps({"username": "trainer", "password": "train123"}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
))
token = json.loads(resp.read())["access_token"]
print(f"Token: {token[:30]}...")

# === Step 3: Start training ===
print("\n=== Start training ===")
data = json.dumps({
    "scene_id": 1,
    "model_name": "yolo11n",
    "epochs": 5,
    "batch_size": 16,
    "img_size": 640,
    "device": "0",
    "optimizer": "SGD",
    "lr0": 0.01,
    "dataset_path": "datasets/pcb_defect",
}).encode()
try:
    resp = urllib.request.urlopen(urllib.request.Request(
        f"{BASE}/api/training/start",
        data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    ))
    print(json.dumps(json.loads(resp.read()), indent=2, ensure_ascii=False))
except urllib.error.HTTPError as e:
    print(f"FAILED: {e.code} - {e.read().decode()}")

print(f"\n=== Monitor: {BASE}/api/training/status/XXX ===")
