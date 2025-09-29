"""
Модуль для визуализации 3D моделей в веб-браузере
Автор: Алексей Марышев
"""

import json
from typing import Dict, List, Any, Optional
import streamlit.components.v1 as components
from loguru import logger


class Web3DViewer:
    """Класс для отображения 3D моделей в браузере на основе инструкций"""
    
    @staticmethod
    def generate_threejs_html(instructions: Dict[str, Any], width: int = 800, height: int = 600) -> str:
        """
        Генерирует HTML с Three.js для отображения 3D модели
        
        Args:
            instructions: Инструкции для построения модели
            width: Ширина окна просмотра
            height: Высота окна просмотра
            
        Returns:
            HTML код с 3D сценой
        """
        
        # Конвертируем инструкции в JavaScript объекты
        components_js = Web3DViewer._convert_components_to_js(instructions.get('components', []))
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ margin: 0; overflow: hidden; }}
                #info {{
                    position: absolute;
                    top: 10px;
                    left: 10px;
                    color: white;
                    font-family: Arial;
                    background: rgba(0,0,0,0.5);
                    padding: 10px;
                    border-radius: 5px;
                }}
            </style>
        </head>
        <body>
            <div id="info">
                🏗️ 3D Модель | Используйте мышь для вращения<br>
                Колесико - масштаб | ПКМ - перемещение
            </div>
            
            <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
            
            <script>
                // Создаем сцену
                const scene = new THREE.Scene();
                scene.background = new THREE.Color(0xf0f0f0);
                
                // Камера
                const camera = new THREE.PerspectiveCamera(
                    75, {width}/{height}, 0.1, 1000
                );
                camera.position.set(20, 20, 20);
                camera.lookAt(0, 0, 0);
                
                // Рендерер
                const renderer = new THREE.WebGLRenderer({{ antialias: true }});
                renderer.setSize({width}, {height});
                renderer.shadowMap.enabled = true;
                document.body.appendChild(renderer.domElement);
                
                // Контролы для управления камерой
                const controls = new THREE.OrbitControls(camera, renderer.domElement);
                controls.enableDamping = true;
                controls.dampingFactor = 0.05;
                
                // Освещение
                const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
                scene.add(ambientLight);
                
                const directionalLight = new THREE.DirectionalLight(0xffffff, 0.4);
                directionalLight.position.set(10, 20, 10);
                directionalLight.castShadow = true;
                scene.add(directionalLight);
                
                // Сетка для пола
                const gridHelper = new THREE.GridHelper(50, 50, 0x888888, 0xcccccc);
                scene.add(gridHelper);
                
                // Оси координат
                const axesHelper = new THREE.AxesHelper(10);
                scene.add(axesHelper);
                
                // Материалы
                const materials = {{
                    'бетон': new THREE.MeshLambertMaterial({{ color: 0x808080 }}),
                    'стекло': new THREE.MeshPhysicalMaterial({{ 
                        color: 0x88ccff, 
                        transparent: true, 
                        opacity: 0.6,
                        roughness: 0.1,
                        metalness: 0.1
                    }}),
                    'дерево': new THREE.MeshLambertMaterial({{ color: 0x8B4513 }}),
                    'металл': new THREE.MeshStandardMaterial({{ 
                        color: 0xaaaaaa,
                        metalness: 0.8,
                        roughness: 0.2
                    }}),
                    'кирпич': new THREE.MeshLambertMaterial({{ color: 0xB22222 }}),
                    'default': new THREE.MeshNormalMaterial()
                }};
                
                // Функция создания примитивов
                function createPrimitive(component) {{
                    let geometry;
                    const type = component.type || 'cube';
                    const scale = component.scale || [1, 1, 1];
                    
                    switch(type.toLowerCase()) {{
                        case 'cube':
                        case 'box':
                            geometry = new THREE.BoxGeometry(scale[0], scale[1], scale[2]);
                            break;
                        case 'sphere':
                            geometry = new THREE.SphereGeometry(scale[0], 32, 16);
                            break;
                        case 'cylinder':
                            geometry = new THREE.CylinderGeometry(scale[0], scale[0], scale[1], 32);
                            break;
                        case 'cone':
                            geometry = new THREE.ConeGeometry(scale[0], scale[1], 32);
                            break;
                        case 'plane':
                            geometry = new THREE.PlaneGeometry(scale[0], scale[1]);
                            break;
                        default:
                            geometry = new THREE.BoxGeometry(scale[0], scale[1], scale[2]);
                    }}
                    
                    const materialName = component.material || 'default';
                    const material = materials[materialName] || materials['default'];
                    
                    const mesh = new THREE.Mesh(geometry, material);
                    
                    // Позиционирование
                    const position = component.position || [0, 0, 0];
                    mesh.position.set(position[0], position[1], position[2]);
                    
                    // Вращение
                    const rotation = component.rotation || [0, 0, 0];
                    mesh.rotation.set(
                        rotation[0] * Math.PI / 180,
                        rotation[1] * Math.PI / 180,
                        rotation[2] * Math.PI / 180
                    );
                    
                    mesh.castShadow = true;
                    mesh.receiveShadow = true;
                    
                    return mesh;
                }}
                
                // Добавляем компоненты из инструкций
                const components = {components_js};
                
                // Группа для всех объектов модели
                const modelGroup = new THREE.Group();
                
                components.forEach(component => {{
                    try {{
                        const mesh = createPrimitive(component);
                        modelGroup.add(mesh);
                    }} catch(e) {{
                        console.error('Ошибка создания компонента:', e);
                    }}
                }});
                
                scene.add(modelGroup);
                
                // Центрируем модель
                const box = new THREE.Box3().setFromObject(modelGroup);
                const center = box.getCenter(new THREE.Vector3());
                modelGroup.position.sub(center);
                
                // Анимация
                function animate() {{
                    requestAnimationFrame(animate);
                    controls.update();
                    renderer.render(scene, camera);
                }}
                
                animate();
                
                // Обработка изменения размера окна
                window.addEventListener('resize', () => {{
                    camera.aspect = window.innerWidth / window.innerHeight;
                    camera.updateProjectionMatrix();
                    renderer.setSize(window.innerWidth, window.innerHeight);
                }});
            </script>
        </body>
        </html>
        """
        
        return html
    
    @staticmethod
    def _convert_components_to_js(components: List[Dict]) -> str:
        """Конвертирует компоненты в JavaScript массив"""
        
        # Если компонентов нет, создаем демонстрационные
        if not components:
            components = [
                {
                    "name": "Основание",
                    "type": "cube",
                    "position": [0, 0.5, 0],
                    "scale": [10, 1, 10],
                    "material": "бетон"
                },
                {
                    "name": "Стена 1",
                    "type": "cube",
                    "position": [-4.5, 3, 0],
                    "scale": [1, 5, 10],
                    "material": "кирпич"
                },
                {
                    "name": "Стена 2",
                    "type": "cube",
                    "position": [4.5, 3, 0],
                    "scale": [1, 5, 10],
                    "material": "кирпич"
                },
                {
                    "name": "Крыша",
                    "type": "cone",
                    "position": [0, 7, 0],
                    "scale": [7, 3, 7],
                    "material": "металл"
                }
            ]
        
        return json.dumps(components)
    
    @staticmethod
    def render_3d_view(instructions: Dict[str, Any], key: str = "3d_viewer") -> None:
        """
        Отображает 3D модель в Streamlit
        
        Args:
            instructions: Инструкции для построения модели
            key: Уникальный ключ компонента
        """
        
        try:
            html_content = Web3DViewer.generate_threejs_html(instructions)
            
            # Отображаем в iframe
            components.html(
                html_content,
                height=600,
                scrolling=False
            )
            
            logger.success("3D модель успешно отображена")
            
        except Exception as e:
            logger.error(f"Ошибка при отображении 3D модели: {e}")
            raise
    
    @staticmethod
    def generate_babylon_viewer(instructions: Dict[str, Any]) -> str:
        """
        Альтернативный вариант с Babylon.js для более сложных сцен
        """
        components_js = Web3DViewer._convert_components_to_js(instructions.get('components', []))
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                html, body {{
                    overflow: hidden;
                    width: 100%;
                    height: 100%;
                    margin: 0;
                    padding: 0;
                }}
                #renderCanvas {{
                    width: 100%;
                    height: 100%;
                    touch-action: none;
                }}
            </style>
        </head>
        <body>
            <canvas id="renderCanvas"></canvas>
            
            <script src="https://cdn.babylonjs.com/babylon.js"></script>
            <script>
                const canvas = document.getElementById("renderCanvas");
                const engine = new BABYLON.Engine(canvas, true);
                
                const createScene = () => {{
                    const scene = new BABYLON.Scene(engine);
                    scene.clearColor = new BABYLON.Color3(0.95, 0.95, 0.95);
                    
                    // Камера
                    const camera = new BABYLON.ArcRotateCamera(
                        "camera", 
                        Math.PI / 4, 
                        Math.PI / 3, 
                        30, 
                        BABYLON.Vector3.Zero(), 
                        scene
                    );
                    camera.attachControl(canvas, true);
                    camera.wheelPrecision = 20;
                    
                    // Освещение
                    const light = new BABYLON.HemisphericLight(
                        "light", 
                        new BABYLON.Vector3(0, 1, 0), 
                        scene
                    );
                    light.intensity = 0.7;
                    
                    // Земля
                    const ground = BABYLON.MeshBuilder.CreateGround(
                        "ground", 
                        {{width: 50, height: 50}}, 
                        scene
                    );
                    ground.material = new BABYLON.StandardMaterial("groundMat", scene);
                    ground.material.diffuseColor = new BABYLON.Color3(0.8, 0.8, 0.8);
                    
                    // Добавляем компоненты
                    const components = {components_js};
                    
                    components.forEach(comp => {{
                        let mesh;
                        const type = comp.type || 'cube';
                        
                        switch(type.toLowerCase()) {{
                            case 'cube':
                            case 'box':
                                mesh = BABYLON.MeshBuilder.CreateBox(
                                    comp.name || "box", 
                                    {{
                                        width: comp.scale ? comp.scale[0] : 1,
                                        height: comp.scale ? comp.scale[1] : 1,
                                        depth: comp.scale ? comp.scale[2] : 1
                                    }}, 
                                    scene
                                );
                                break;
                            case 'sphere':
                                mesh = BABYLON.MeshBuilder.CreateSphere(
                                    comp.name || "sphere",
                                    {{diameter: comp.scale ? comp.scale[0] * 2 : 2}},
                                    scene
                                );
                                break;
                            case 'cylinder':
                                mesh = BABYLON.MeshBuilder.CreateCylinder(
                                    comp.name || "cylinder",
                                    {{
                                        diameter: comp.scale ? comp.scale[0] * 2 : 2,
                                        height: comp.scale ? comp.scale[1] : 2
                                    }},
                                    scene
                                );
                                break;
                            default:
                                mesh = BABYLON.MeshBuilder.CreateBox(
                                    comp.name || "box",
                                    {{size: 1}},
                                    scene
                                );
                        }}
                        
                        // Позиция
                        if (comp.position) {{
                            mesh.position = new BABYLON.Vector3(
                                comp.position[0],
                                comp.position[1],
                                comp.position[2]
                            );
                        }}
                        
                        // Материал
                        const material = new BABYLON.StandardMaterial(comp.name + "Mat", scene);
                        
                        switch(comp.material) {{
                            case 'бетон':
                                material.diffuseColor = new BABYLON.Color3(0.5, 0.5, 0.5);
                                break;
                            case 'стекло':
                                material.diffuseColor = new BABYLON.Color3(0.5, 0.8, 1);
                                material.alpha = 0.6;
                                break;
                            case 'дерево':
                                material.diffuseColor = new BABYLON.Color3(0.55, 0.27, 0.07);
                                break;
                            case 'металл':
                                material.diffuseColor = new BABYLON.Color3(0.7, 0.7, 0.7);
                                material.specularColor = new BABYLON.Color3(1, 1, 1);
                                break;
                            case 'кирпич':
                                material.diffuseColor = new BABYLON.Color3(0.7, 0.13, 0.13);
                                break;
                            default:
                                material.diffuseColor = new BABYLON.Color3(
                                    Math.random(),
                                    Math.random(),
                                    Math.random()
                                );
                        }}
                        
                        mesh.material = material;
                    }});
                    
                    return scene;
                }};
                
                const scene = createScene();
                
                engine.runRenderLoop(() => {{
                    scene.render();
                }});
                
                window.addEventListener("resize", () => {{
                    engine.resize();
                }});
            </script>
        </body>
        </html>
        """
        
        return html


def test_3d_viewer():
    """Тестирование 3D визуализатора"""
    
    test_instructions = {
        "object_type": "building",
        "style": "modern",
        "components": [
            {
                "name": "Foundation",
                "type": "cube",
                "position": [0, 0.5, 0],
                "scale": [15, 1, 15],
                "material": "бетон"
            },
            {
                "name": "First Floor",
                "type": "cube",
                "position": [0, 3, 0],
                "scale": [12, 5, 12],
                "material": "стекло"
            },
            {
                "name": "Second Floor",
                "type": "cube",
                "position": [0, 8, 0],
                "scale": [10, 4, 10],
                "material": "стекло"
            },
            {
                "name": "Roof",
                "type": "cube",
                "position": [0, 11, 0],
                "scale": [11, 0.5, 11],
                "material": "бетон"
            }
        ]
    }
    
    html = Web3DViewer.generate_threejs_html(test_instructions)
    
    with open("test_3d_view.html", "w", encoding="utf-8") as f:
        f.write(html)
    
    logger.success("Тестовый HTML файл создан: test_3d_view.html")
    

if __name__ == "__main__":
    test_3d_viewer()