/**
 * Three.js Module Loader
 * 将 ES Modules 暴露到全局作用域，供 graph-viz.js 使用
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';

// 暴露到全局作用域（直接放在 window 上，而不是 THREE 对象上）
window.THREE = THREE;
window.OrbitControls = OrbitControls;
window.EffectComposer = EffectComposer;
window.RenderPass = RenderPass;
window.UnrealBloomPass = UnrealBloomPass;

console.log('[ThreeLoader] Three.js ES Modules 已加载到全局作用域');
console.log('[ThreeLoader] THREE:', typeof THREE);
console.log('[ThreeLoader] OrbitControls:', typeof OrbitControls);

// 触发自定义事件，通知 Three.js 已加载完成
window.dispatchEvent(new CustomEvent('three-loaded'));
