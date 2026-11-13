// Interactive CAD viewer.
//
// Usage:
//   <div class="cad-viewer" data-model="assets/model.glb" data-up-axis="y">
//     <button class="cad-label" data-node="Front Wing Assembly" style="--label-color:#1f6fb2">
//       <strong>Front Wing</strong><span>Owner</span>
//     </button>
//   </div>
//
// Supports .stl, .glb and .gltf. Drag to rotate, scroll to zoom, right-drag to pan.
// Each .cad-label is pinned above the model node named in data-node (or above
// data-anchor, if given, e.g. one side of a symmetric pair); hovering or tapping
// a label fades out everything except data-node.
// data-up-axis: "y" for glTF/GLB (default), "z" for Z-up STL exports.
// data-auto-rotate="false" disables the idle spin.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { STLLoader } from "three/addons/loaders/STLLoader.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

function loadModel(url) {
	const ext = url.split("?")[0].split(".").pop().toLowerCase();
	return new Promise((resolve, reject) => {
		if (ext === "stl") {
			new STLLoader().load(
				url,
				(geometry) => {
					geometry.computeVertexNormals();
					const material = new THREE.MeshStandardMaterial({ color: 0x9aa7b4, metalness: 0.15, roughness: 0.55 });
					resolve(new THREE.Mesh(geometry, material));
				},
				undefined,
				reject,
			);
		} else if (ext === "glb" || ext === "gltf") {
			new GLTFLoader().load(url, (gltf) => resolve(gltf.scene), undefined, reject);
		} else {
			reject(new Error(`Unsupported model format: .${ext}`));
		}
	});
}

function initViewer(container) {
	const url = container.dataset.model;
	const labels = [...container.querySelectorAll(".cad-label")];

	const status = document.createElement("div");
	status.className = "cad-viewer-status";
	status.textContent = "Loading 3D model…";
	container.appendChild(status);

	const renderer = new THREE.WebGLRenderer({ antialias: true });
	renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
	renderer.toneMapping = THREE.ACESFilmicToneMapping;
	container.prepend(renderer.domElement);

	const scene = new THREE.Scene();
	scene.background = new THREE.Color(0xf4f7fa);
	scene.environment = new THREE.PMREMGenerator(renderer).fromScene(new RoomEnvironment(), 0.04).texture;
	const key = new THREE.DirectionalLight(0xffffff, 1.2);
	key.position.set(1, 2, 1.5);
	scene.add(key, new THREE.HemisphereLight(0xffffff, 0x8a96a3, 0.6));

	const camera = new THREE.PerspectiveCamera(35, 1, 0.01, 100);
	const controls = new OrbitControls(camera, renderer.domElement);
	controls.enableDamping = true;
	controls.minDistance = 0.8;
	controls.maxDistance = 10;
	controls.autoRotate = container.dataset.autoRotate !== "false";
	controls.autoRotateSpeed = 0.8;
	controls.addEventListener("start", () => (controls.autoRotate = false));

	function resize() {
		camera.aspect = container.clientWidth / container.clientHeight;
		camera.updateProjectionMatrix();
		renderer.setSize(container.clientWidth, container.clientHeight, false);
	}
	new ResizeObserver(resize).observe(container);
	resize();

	const anchors = []; // { label, point }
	const meshes = [];
	const fadeMaterial = new THREE.MeshStandardMaterial({ color: 0xc9d2db, transparent: true, opacity: 0.18, depthWrite: false });

	function focus(node) {
		labels.forEach((l) => l.classList.toggle("is-dimmed", node && l._node !== node));
		for (const m of meshes) {
			let inFocus = !node;
			for (let p = m; p && !inFocus; p = p.parent) inFocus = p === node;
			m.material = inFocus ? m.userData.material : fadeMaterial;
		}
	}

	loadModel(url)
		.then((object) => {
			if (container.dataset.upAxis === "z") object.rotation.x = -Math.PI / 2;
			const maxAniso = renderer.capabilities.getMaxAnisotropy();
			object.traverse((o) => {
				if (o.isMesh) {
					// CAD exports often disable mipmaps, which makes fine textures (carbon weave) shimmer.
					for (const mat of [].concat(o.material)) {
						if (mat.map && !mat.map.userData.fixed) {
							mat.map.minFilter = THREE.LinearMipmapLinearFilter;
							mat.map.generateMipmaps = true;
							mat.map.anisotropy = maxAniso;
							mat.map.needsUpdate = true;
							mat.map.userData.fixed = true;
						}
					}
					o.userData.material = o.material;
					meshes.push(o);
				}
			});

			// Centre the model at the origin and scale it to a 2-unit size.
			const pivot = new THREE.Group();
			pivot.add(object);
			scene.add(pivot);
			pivot.updateMatrixWorld(true);
			const box = new THREE.Box3().setFromObject(object);
			const size = box.getSize(new THREE.Vector3());
			object.position.sub(box.getCenter(new THREE.Vector3()));
			pivot.scale.setScalar(2 / Math.max(size.x, size.y, size.z));
			pivot.updateMatrixWorld(true);

			for (const label of labels) {
				// GLTFLoader sanitises node names (spaces -> underscores), so try both forms.
				const find = (name) => name && (object.getObjectByName(name) || object.getObjectByName(THREE.PropertyBinding.sanitizeNodeName(name)));
				const node = find(label.dataset.node);
				const anchor = find(label.dataset.anchor) || node;
				if (!node) {
					console.warn(`cad-viewer: no node named "${label.dataset.node}"`);
					label.hidden = true;
					continue;
				}
				const b = new THREE.Box3().setFromObject(anchor);
				const point = b.getCenter(new THREE.Vector3());
				point.y = b.max.y; // pin to the top of the part
				label._node = node;
				anchors.push({ label, point });
				label.addEventListener("pointerenter", () => focus(node));
				label.addEventListener("pointerleave", () => focus(null));
				label.addEventListener("focus", () => focus(node));
				label.addEventListener("blur", () => focus(null));
			}

			camera.position.set(1.75, 1.15, 1.75);
			controls.update();
			status.remove();
			container.classList.add("is-loaded");
		})
		.catch((err) => {
			console.error(err);
			status.textContent = "Could not load 3D model.";
		});

	const v = new THREE.Vector3();
	function placeLabels() {
		const w = container.clientWidth;
		const h = container.clientHeight;
		for (const { label, point } of anchors) {
			v.copy(point).project(camera);
			label.style.transform = `translate(${((v.x + 1) / 2) * w}px, ${((1 - v.y) / 2) * h}px)`;
			label.style.zIndex = String(Math.round((1 - v.z) * 1000));
		}
	}

	// Only render while the viewer is on screen.
	let visible = false;
	new IntersectionObserver(([entry]) => (visible = entry.isIntersecting)).observe(container);
	renderer.setAnimationLoop(() => {
		if (!visible) return;
		controls.update();
		renderer.render(scene, camera);
		placeLabels();
	});
}

document.querySelectorAll(".cad-viewer[data-model]").forEach(initViewer);
