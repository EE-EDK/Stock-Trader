/**
 * @file coin_stack.js
 * @brief Three.js coin stack animation: bounce-in, stack to 10, fall over, fall down, repeat.
 * @details Single-file simulation per WebGL protocol: World Anchor, Asset Factory, Kinematic Kernel, Director.
 */
(function() {
    'use strict';

    const LANDING_X = 9;            // Stack near gear (right side, per purple lines)
    const BOUNCE_START_X = -9.5;    // Left side – coin appears "from nowhere" here
    const COIN_RADIUS = 0.88;       // ~size of "S" in Settings (purple circle reference)
    const COIN_HEIGHT = 0.18;
    const BOUNCE_HORIZONTAL_SPEED = 5.5;
    const NUM_BOUNCES = 6;          // Zig-zag: top-to-bottom-to-top bounces across screen
    const TOP_Y = 4.2;              // Top of nav strip (bounce ceiling)
    const BOTTOM_Y = -4.2;          // Bottom of nav strip (bounce floor)
    const GRAVITY = 28;
    const FALL_SPEED = (28 * 0.5) / 3;  // Fall 3x slower than before
    const FALL_OVER_ANGULAR = 2.5;
    const WORLD_BOUNDS = { yFloor: -8 };

    let scene, camera, renderer, clock;
    let coinGroup, coins = [], stackBaseY = 0;
    let state = 'BOUNCE';
    let activeCoin = null;
    let stackCount = 0;
    let fallOverAngle = 0;
    let fallOverDuration = 0.8;

    function initWorldAnchor(container) {
        scene = new THREE.Scene();
        scene.background = new THREE.Color(0x252a33);

        const w = container.clientWidth || 280;
        const h = 56;
        camera = new THREE.OrthographicCamera(-10, 10, 6, -6, 0.1, 100);
        camera.position.set(0, 0, 15);
        camera.lookAt(0, 0, 0);

        // Lighting rig for shiny metal: key + fill + rim so the coin catches light as it rolls
        const hemi = new THREE.HemisphereLight(0xfff5e0, 0x2a2520, 0.4);
        scene.add(hemi);
        const keyLight = new THREE.DirectionalLight(0xfff8e0, 2.0);
        keyLight.position.set(6, 10, 8);
        keyLight.castShadow = false;
        scene.add(keyLight);
        const fillLight = new THREE.DirectionalLight(0xffe8b0, 0.8);
        fillLight.position.set(-4, 2, 5);
        scene.add(fillLight);
        const rimLight = new THREE.DirectionalLight(0xffd700, 1.0);
        rimLight.position.set(-3, 4, -6);
        scene.add(rimLight);

        renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.setSize(w, h);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        if (renderer.toneMapping !== undefined) {
            renderer.toneMapping = THREE.ACESFilmicToneMapping;
            renderer.toneMappingExposure = 1.0;
        }
        if (renderer.outputEncoding !== undefined) renderer.outputEncoding = THREE.sRGBEncoding;
        container.appendChild(renderer.domElement);
        renderer.domElement.style.display = 'block';
        renderer.domElement.style.width = '100%';
        renderer.domElement.style.height = '100%';

        clock = new THREE.Clock();
        coinGroup = new THREE.Group();
        scene.add(coinGroup);
    }

    function createDollarTexture() {
        const size = 128;
        const canvas = document.createElement('canvas');
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#2a2d35';
        ctx.fillRect(0, 0, size, size);
        ctx.fillStyle = '#e8b828';
        ctx.font = 'bold 72px system-ui, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('$', size / 2, size / 2);
        const tex = new THREE.CanvasTexture(canvas);
        tex.needsUpdate = true;
        return tex;
    }

    function createCoinMesh() {
        const root = new THREE.Group();

        const goldMat = new THREE.MeshStandardMaterial({
            color: 0xe8b828,
            metalness: 0.96,
            roughness: 0.1,
            envMapIntensity: 1
        });

        const edgeMat = new THREE.MeshStandardMaterial({
            color: 0xd4a810,
            metalness: 0.95,
            roughness: 0.12
        });

        const cyl = new THREE.CylinderGeometry(COIN_RADIUS, COIN_RADIUS, COIN_HEIGHT, 32);
        const cylMesh = new THREE.Mesh(cyl, goldMat);
        cylMesh.rotation.x = Math.PI / 2;
        root.add(cylMesh);

        const faceGeo = new THREE.CircleGeometry(COIN_RADIUS * 0.98, 32);
        const faceMat = new THREE.MeshStandardMaterial({
            color: 0xe8b828,
            metalness: 0.94,
            roughness: 0.1,
            map: createDollarTexture()
        });
        const face = new THREE.Mesh(faceGeo, faceMat);
        face.rotation.x = -Math.PI / 2;
        face.position.z = COIN_HEIGHT / 2 + 0.002;
        root.add(face);

        const backFace = new THREE.Mesh(faceGeo, goldMat);
        backFace.rotation.x = Math.PI / 2;
        backFace.position.z = -COIN_HEIGHT / 2 - 0.002;
        root.add(backFace);

        return root;
    }

    function zigzagY(t) {
        if (t >= 1) return stackBaseY + COIN_HEIGHT / 2;
        const seg = Math.floor(t * NUM_BOUNCES);
        const s = (t * NUM_BOUNCES) % 1;
        if (seg % 2 === 0) return TOP_Y + s * (BOTTOM_Y - TOP_Y);
        return BOTTOM_Y + s * (TOP_Y - BOTTOM_Y);
    }

    function spawnBouncingCoin() {
        const mesh = createCoinMesh();
        mesh.position.set(BOUNCE_START_X, TOP_Y, 0);
        mesh.userData.vel = new THREE.Vector3(BOUNCE_HORIZONTAL_SPEED, 0, 0);
        mesh.userData.landed = false;
        coinGroup.add(mesh);
        activeCoin = mesh;
        return mesh;
    }

    function updateBouncePhysics(mesh, dt) {
        if (mesh.userData.landed) return;
        const p = mesh.position;
        const totalDist = LANDING_X - BOUNCE_START_X;
        p.x += mesh.userData.vel.x * dt;
        const t = Math.min(1, (p.x - BOUNCE_START_X) / totalDist);
        p.y = zigzagY(t);
        mesh.rotation.y += (mesh.userData.vel.x * dt) / COIN_RADIUS;
        mesh.rotation.x = t * NUM_BOUNCES * Math.PI;
        if (p.x >= LANDING_X) {
            p.x = LANDING_X;
            p.y = stackBaseY + COIN_HEIGHT / 2;
            mesh.userData.vel.set(0, 0, 0);
            mesh.userData.landed = true;
            mesh.rotation.x = 0;
        }
    }

    function tick() {
        const dt = Math.min(clock.getDelta(), 0.05);
        const elapsed = clock.getElapsedTime();

        if (state === 'BOUNCE') {
            if (!activeCoin) {
                activeCoin = spawnBouncingCoin();
                coins.push(activeCoin);
            }
            updateBouncePhysics(activeCoin, dt);
            if (activeCoin.userData.landed) {
                stackBaseY += COIN_HEIGHT;
                stackCount++;
                activeCoin = null;
                if (stackCount >= 10) {
                    state = 'FALL_OVER';
                    fallOverAngle = 0;
                } else {
                    setTimeout(function() { spawnBouncingCoin(); }, 200);
                }
            }
        } else if (state === 'FALL_OVER') {
            fallOverAngle += FALL_OVER_ANGULAR * dt;
            const tip = Math.min(fallOverAngle, Math.PI / 2);
            coinGroup.rotation.z = tip;
            if (fallOverAngle >= Math.PI / 2) {
                state = 'FALL_DOWN';
                coinGroup.rotation.z = Math.PI / 2;
                coins.forEach(function(m) {
                    m.userData.vel = new THREE.Vector3(0, 0, 0);
                });
            }
        } else if (state === 'FALL_DOWN') {
            coinGroup.position.y -= FALL_SPEED * dt;
            if (coinGroup.position.y < WORLD_BOUNDS.yFloor) {
                state = 'RESET';
            }
        } else if (state === 'RESET') {
            while (coinGroup.children.length) coinGroup.remove(coinGroup.children[0]);
            coins = [];
            stackBaseY = 0;
            stackCount = 0;
            activeCoin = null;
            coinGroup.rotation.z = 0;
            coinGroup.position.y = 0;
            state = 'BOUNCE';
            setTimeout(function() { spawnBouncingCoin(); }, 400);
        }

        renderer.render(scene, camera);
        requestAnimationFrame(tick);
    }

    function onResize(container) {
        const w = container.clientWidth || 280;
        const h = 56;
        if (renderer) {
            renderer.setSize(w, h);
            const half = 10;
            camera.left = -half;
            camera.right = half;
            camera.top = 6;
            camera.bottom = -6;
            camera.updateProjectionMatrix();
        }
    }

    function start(container) {
        if (!container) return;
        initWorldAnchor(container);
        state = 'BOUNCE';
        stackCount = 0;
        stackBaseY = 0;
        coins = [];
        activeCoin = null;
        setTimeout(function() { spawnBouncingCoin(); }, 300);
        tick();
        const ro = new ResizeObserver(function() { onResize(container); });
        ro.observe(container);
    }

    window.StockTraderCoinStack = { start: start };
})();
