/**
 * @file coin_stack.js
 * @brief Three.js coin stack animation: bounce-in, stack to 10, fall over, fall down, repeat.
 * @details Single-file simulation per WebGL protocol: World Anchor, Asset Factory, Kinematic Kernel, Director.
 */
(function() {
    'use strict';

    const LANDING_X = 10.4;         // Stack right up to the gear (camera right is 11)
    const BOUNCE_START_X = -10.4;   // Left edge – coin appears from nowhere; nothing else on left
    const COIN_RADIUS = 0.88;       // ~size of "S" in Settings
    const COIN_HEIGHT = 0.5;        // Thick disc so stack shows distinct coins (reference images)
    const BOUNCE_HORIZONTAL_SPEED = 9.2;  // Fast enough to reach gear in ~2.3s
    const NUM_BOUNCES = 10;         // Zig-zag all the way across to gear
    const TOP_Y = 4.2;
    const BOTTOM_Y = -4.2;
    const STACK_X_OFFSET = 0.5;     // Imperfect stack: visible left/right wobble per coin
    const STACK_Z_OFFSET = 0.2;
    const FALL_SPEED = 5.2;         // Steady downward speed (GIF: consistent gravity-like fall)
    const FALL_DRIFT = 0.15;       // Slight horizontal drift per coin
    const FALL_TUMBLE_MIN = 2.5;   // Multi-axis tumble like GIF (spin + flip)
    const FALL_TUMBLE_MAX = 5.5;
    const FALL_OVER_ANGULAR = 2.5;
    const WORLD_BOUNDS = { yFloor: -100 };  // Fall to bottom of page before reset

    let scene, camera, renderer, clock;
    let stackGroup, bouncerGroup;    // stack = landed right side only; bouncer = single coin from nowhere
    let coins = [], stackBaseY = 0;
    let fallingCoins = [];           // Coins released and tumbling down (GIF-style)
    let state = 'BOUNCE';
    let activeCoin = null;
    let stackCount = 0;
    let fallOverAngle = 0;

    function initWorldAnchor(container) {
        scene = new THREE.Scene();
        scene.background = new THREE.Color(0x252a33);

        const w = container.clientWidth || 280;
        const h = 56;
        camera = new THREE.OrthographicCamera(-12, 12, 6, -6, 0.1, 100);
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
        stackGroup = new THREE.Group();
        bouncerGroup = new THREE.Group();
        scene.add(stackGroup);
        scene.add(bouncerGroup);
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
            color: 0x8b6914,
            metalness: 0.9,
            roughness: 0.18
        });

        const cyl = new THREE.CylinderGeometry(COIN_RADIUS, COIN_RADIUS, COIN_HEIGHT, 32);
        const cylMesh = new THREE.Mesh(cyl, edgeMat);
        cylMesh.rotation.x = Math.PI / 2;
        root.add(cylMesh);

        const rimTorus = new THREE.TorusGeometry(COIN_RADIUS - 0.02, 0.045, 8, 32);
        const rimFront = new THREE.Mesh(rimTorus, edgeMat);
        rimFront.rotation.x = Math.PI / 2;
        rimFront.position.z = COIN_HEIGHT / 2;
        root.add(rimFront);
        const rimBack = new THREE.Mesh(rimTorus.clone(), edgeMat);
        rimBack.rotation.x = Math.PI / 2;
        rimBack.position.z = -COIN_HEIGHT / 2;
        root.add(rimBack);

        const faceGeo = new THREE.CircleGeometry(COIN_RADIUS * 0.92, 32);
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
        while (bouncerGroup.children.length > 0) bouncerGroup.remove(bouncerGroup.children[0]);
        const mesh = createCoinMesh();
        mesh.position.set(BOUNCE_START_X, TOP_Y, 0);
        mesh.userData.vel = new THREE.Vector3(BOUNCE_HORIZONTAL_SPEED, 0, 0);
        mesh.userData.landed = false;
        bouncerGroup.add(mesh);
        activeCoin = mesh;
        return mesh;
    }

    function releaseCoinsToFall() {
        stackGroup.updateMatrixWorld(true);
        const worldPos = new THREE.Vector3();
        const kids = stackGroup.children.slice();
        for (let i = 0; i < kids.length; i++) {
            const coin = kids[i];
            coin.getWorldPosition(worldPos);
            stackGroup.remove(coin);
            scene.add(coin);
            coin.position.copy(worldPos);
            coin.rotation.set(
                Math.random() * Math.PI * 2,
                Math.random() * Math.PI * 2,
                Math.random() * Math.PI * 2
            );
            coin.userData.tumbleX = FALL_TUMBLE_MIN + Math.random() * (FALL_TUMBLE_MAX - FALL_TUMBLE_MIN);
            coin.userData.tumbleY = FALL_TUMBLE_MIN + Math.random() * (FALL_TUMBLE_MAX - FALL_TUMBLE_MIN);
            coin.userData.tumbleZ = FALL_TUMBLE_MIN + Math.random() * (FALL_TUMBLE_MAX - FALL_TUMBLE_MIN);
            if (Math.random() < 0.5) coin.userData.tumbleX *= -1;
            if (Math.random() < 0.5) coin.userData.tumbleY *= -1;
            if (Math.random() < 0.5) coin.userData.tumbleZ *= -1;
            coin.userData.driftX = (Math.random() - 0.5) * 2 * FALL_DRIFT;
            coin.userData.driftZ = (Math.random() - 0.5) * 2 * FALL_DRIFT;
            fallingCoins.push(coin);
        }
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
            mesh.userData.vel.set(0, 0, 0);
            mesh.userData.landed = true;
            mesh.rotation.x = 0;
            mesh.visible = false;
            bouncerGroup.remove(mesh);
            mesh.position.set(
                LANDING_X + (Math.random() - 0.5) * 2 * STACK_X_OFFSET,
                stackBaseY + COIN_HEIGHT / 2,
                (Math.random() - 0.5) * 2 * STACK_Z_OFFSET
            );
            stackGroup.add(mesh);
            mesh.visible = true;
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
                    setTimeout(function() { spawnBouncingCoin(); }, 220);
                }
            }
        } else if (state === 'FALL_OVER') {
            fallOverAngle += FALL_OVER_ANGULAR * dt;
            const tip = Math.min(fallOverAngle, Math.PI / 2);
            stackGroup.rotation.z = tip;
            if (fallOverAngle >= Math.PI / 2) {
                stackGroup.rotation.z = Math.PI / 2;
                releaseCoinsToFall();
                state = 'FALL_DOWN';
            }
        } else if (state === 'FALL_DOWN') {
            const stillFalling = [];
            for (let i = 0; i < fallingCoins.length; i++) {
                const coin = fallingCoins[i];
                coin.position.y -= FALL_SPEED * dt;
                coin.position.x += coin.userData.driftX * dt;
                coin.position.z += coin.userData.driftZ * dt;
                coin.rotation.x += coin.userData.tumbleX * dt;
                coin.rotation.y += coin.userData.tumbleY * dt;
                coin.rotation.z += coin.userData.tumbleZ * dt;
                if (coin.position.y > WORLD_BOUNDS.yFloor) stillFalling.push(coin);
                else scene.remove(coin);
            }
            fallingCoins = stillFalling;
            if (fallingCoins.length === 0) state = 'RESET';
        } else if (state === 'RESET') {
            while (stackGroup.children.length) stackGroup.remove(stackGroup.children[0]);
            while (bouncerGroup.children.length) bouncerGroup.remove(bouncerGroup.children[0]);
            for (let i = 0; i < fallingCoins.length; i++) scene.remove(fallingCoins[i]);
            fallingCoins = [];
            coins = [];
            stackBaseY = 0;
            stackCount = 0;
            activeCoin = null;
            stackGroup.rotation.set(0, 0, 0);
            stackGroup.position.set(0, 0, 0);
            state = 'BOUNCE';
            setTimeout(function() { spawnBouncingCoin(); }, 350);
        }

        renderer.render(scene, camera);
        requestAnimationFrame(tick);
    }

    function onResize(container) {
        const w = container.clientWidth || 280;
        const h = 56;
        if (renderer) {
            renderer.setSize(w, h);
            camera.left = -12;
            camera.right = 12;
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
