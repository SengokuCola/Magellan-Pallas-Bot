import random
import requests
import json
from typing import Dict, Tuple, Optional
from pathlib import Path
import base64

# 中国主要区域的经纬度范围
CHINA_REGIONS = [
    {
        "name": "华北",
        "lat": (35.0, 42.0),
        "lng": (110.0, 120.0)
    },
    {
        "name": "东北",
        "lat": (41.0, 47.0),
        "lng": (120.0, 130.0)
    },
    {
        "name": "华东",
        "lat": (28.0, 35.0),
        "lng": (115.0, 122.0)
    },
    {
        "name": "华中",
        "lat": (28.0, 34.0),
        "lng": (108.0, 116.0)
    },
    {
        "name": "华南",
        "lat": (22.0, 28.0),
        "lng": (108.0, 120.0)
    },
    {
        "name": "西南",
        "lat": (23.0, 33.0),
        "lng": (98.0, 108.0)
    },
    {
        "name": "西北",
        "lat": (33.0, 42.0),
        "lng": (95.0, 110.0)
    }
]

def get_random_coordinates() -> Tuple[float, float]:
    """
    从预定义的中国区域中随机选择一个区域，并在该区域内生成随机坐标
    """
    region = random.choice(CHINA_REGIONS)
    lat = random.uniform(region["lat"][0], region["lat"][1])
    lng = random.uniform(region["lng"][0], region["lng"][1])
    return lat, lng

def get_location_info(latitude: float, longitude: float) -> Optional[Dict]:
    """
    使用高德地图API进行逆地理编码
    """
    try:
        key = "90b2d1143a15c94305068a1ac1660982"
        url = f"https://restapi.amap.com/v3/geocode/regeo?key={key}&location={longitude},{latitude}&poitype=&radius=1000&extensions=all&batch=false&roadlevel=0"
        
        response = requests.get(url, timeout=5)
        data = json.loads(response.text)
        
        if data.get("status") == "1" and data.get("regeocode"):  # 请求成功
            result = data["regeocode"]
            address = result.get("formatted_address", "")
            
            # 获取更详细的地址信息
            component = result.get("addressComponent", {})
            province = component.get("province", "")
            city = component.get("city", "")
            district = component.get("district", "")
            township = component.get("township", "")
            
            # 获取周边POI信息
            pois = result.get("pois", [])
            nearby = [poi.get("name") for poi in pois[:3] if poi.get("name")]
            
            return {
                "address": address,
                "province": province,
                "city": city,
                "district": district,
                "township": township,
                "nearby": nearby
            }
    except Exception as e:
        print(f"获取地理信息失败: {e}")
    return None

def get_map_url(longitude: float, latitude: float) -> str:
    """
    获取指定位置的静态地图URL
    """
    try:
        key = "90b2d1143a15c94305068a1ac1660982"
        params = {
            "location": f"{longitude},{latitude}",  # 中心点坐标
            "zoom": "14",                          # 缩放级别
            "size": "750*500",                     # 图片大小
            "scale": "2",                          # 高清地图
            "markers": f"mid,0xFF0000,A:{longitude},{latitude}",  # 添加标记
            "key": key,
            "traffic": "0",                        # 不显示路况
            "extensions": "all"                    # 返回所有信息
        }
        
        # 构建URL
        base_url = "https://restapi.amap.com/v3/staticmap"
        url_params = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}?{url_params}"
            
    except Exception as e:
        print(f"构建地图URL失败: {e}")
        return ""

def get_random_location() -> Tuple[str, str]:
    """
    生成一个随机的旅游地点坐标并获取详细信息
    
    Returns:
        Tuple[str, str]: (文本消息, 地图URL)
    """
    max_attempts = 3  # 最大尝试次数
    
    for _ in range(max_attempts):
        latitude, longitude = get_random_coordinates()
        location_info = get_location_info(latitude, longitude)
        
        if location_info and location_info["province"]:  # 确保获取到了有效的地址信息
            # 构建回复消息
            location = f"让我看看...这个地方不错：\n"
            location += f"📍 {location_info['province']}"
            if location_info['city']:
                location += f" {location_info['city']}"
            if location_info['district']:
                location += f" {location_info['district']}"
            if location_info['township']:
                location += f" {location_info['township']}"
            
            location += f"\n具体位置：{location_info['address']}"
            
            if location_info['nearby']:
                location += f"\n周边有：{' | '.join(location_info['nearby'])}"
                
            location += f"\n🗺️ 查看地图：https://uri.amap.com/marker?position={longitude},{latitude}&name=推荐地点"
            
            # 获取地图URL
            map_url = get_map_url(longitude, latitude)
            
            return location, map_url
    
    return "唔...这次没找到合适的地方呢，要不要再试试看？", "" 