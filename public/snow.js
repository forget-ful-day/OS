const canvas = document.getElementById('snowfall');
const ctx = canvas.getContext('2d');

let width = 0;
let height = 0;
let flakes = [];

const settings = {
  count: 140,
  minSize: 1.5,
  maxSize: 4.5,
  minSpeed: 0.4,
  maxSpeed: 1.6,
};

const resize = () => {
  width = window.innerWidth;
  height = window.innerHeight;
  canvas.width = width * window.devicePixelRatio;
  canvas.height = height * window.devicePixelRatio;
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;
  ctx.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0);
};

const randomBetween = (min, max) => Math.random() * (max - min) + min;

const createFlake = () => ({
  x: Math.random() * width,
  y: Math.random() * height,
  radius: randomBetween(settings.minSize, settings.maxSize),
  speed: randomBetween(settings.minSpeed, settings.maxSpeed),
  sway: randomBetween(-0.6, 0.6),
  opacity: randomBetween(0.4, 0.9),
});

const populateFlakes = () => {
  flakes = Array.from({ length: settings.count }, createFlake);
};

const updateFlakes = () => {
  flakes.forEach((flake) => {
    flake.y += flake.speed;
    flake.x += flake.sway;

    if (flake.y > height + flake.radius) {
      flake.y = -flake.radius;
      flake.x = Math.random() * width;
    }

    if (flake.x > width + flake.radius) {
      flake.x = -flake.radius;
    } else if (flake.x < -flake.radius) {
      flake.x = width + flake.radius;
    }
  });
};

const drawFlakes = () => {
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';

  flakes.forEach((flake) => {
    ctx.globalAlpha = flake.opacity;
    ctx.beginPath();
    ctx.arc(flake.x, flake.y, flake.radius, 0, Math.PI * 2);
    ctx.fill();
  });
};

const animate = () => {
  updateFlakes();
  drawFlakes();
  requestAnimationFrame(animate);
};

resize();
populateFlakes();
animate();

window.addEventListener('resize', () => {
  resize();
  populateFlakes();
});
