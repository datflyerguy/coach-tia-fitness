// Coach Tia Fitness — light interaction layer. No frameworks/build step
// (this sandbox has no npm access), just small, purposeful vanilla JS.

document.addEventListener("DOMContentLoaded", () => {
  // Only hide .reveal elements once JS has actually taken over (see the
  // .js-ready guard in main.css) — otherwise they're plain visible content.
  document.documentElement.classList.add("js-ready");

  // Mobile nav: hamburger toggles the nav-links dropdown open/closed.
  const navToggle = document.getElementById("nav-toggle");
  const navLinks = document.getElementById("nav-links");
  if (navToggle && navLinks) {
    const openIcon = navToggle.querySelector(".nav-toggle-open");
    const closeIcon = navToggle.querySelector(".nav-toggle-close");
    const setOpen = (open) => {
      navLinks.classList.toggle("open", open);
      navToggle.setAttribute("aria-expanded", open ? "true" : "false");
      if (openIcon) openIcon.style.display = open ? "none" : "";
      if (closeIcon) closeIcon.style.display = open ? "" : "none";
    };
    navToggle.addEventListener("click", () => {
      setOpen(!navLinks.classList.contains("open"));
    });
    // Close after picking a link, and on resize back to desktop width.
    navLinks.querySelectorAll("a").forEach((a) => {
      a.addEventListener("click", () => setOpen(false));
    });
    window.addEventListener("resize", () => {
      if (window.innerWidth > 900) setOpen(false);
    });
  }

  // Scroll-reveal
  const revealEls = document.querySelectorAll(".reveal");
  if (revealEls.length && "IntersectionObserver" in window) {
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("in");
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15 }
    );
    revealEls.forEach((el) => io.observe(el));
  } else {
    revealEls.forEach((el) => el.classList.add("in"));
  }

  // Count-up stat numbers: <span data-countup="73" data-suffix="%">
  document.querySelectorAll("[data-countup]").forEach((el) => {
    const target = parseFloat(el.getAttribute("data-countup"));
    const suffix = el.getAttribute("data-suffix") || "";
    const duration = 1100;
    let start = null;
    const step = (ts) => {
      if (start === null) start = ts;
      const progress = Math.min((ts - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const value = Math.round(target * eased);
      el.textContent = value + suffix;
      if (progress < 1) requestAnimationFrame(step);
    };
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            requestAnimationFrame(step);
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.4 }
    );
    io.observe(el);
  });

  // Hero particle field: a quiet drift of small nodes with faint connecting
  // lines when close together, gold/cyan tinted. Purely decorative, low
  // opacity, respects reduced-motion.
  const canvas = document.getElementById("hero-canvas");
  if (canvas && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    const ctx = canvas.getContext("2d");
    let w, h, particles;

    function resize() {
      w = canvas.width = canvas.offsetWidth * devicePixelRatio;
      h = canvas.height = canvas.offsetHeight * devicePixelRatio;
    }

    function makeParticles() {
      const count = Math.max(28, Math.floor((w * h) / 90000));
      particles = Array.from({ length: count }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.25 * devicePixelRatio,
        vy: (Math.random() - 0.5) * 0.25 * devicePixelRatio,
        r: (Math.random() * 1.4 + 0.6) * devicePixelRatio,
        gold: Math.random() > 0.6,
      }));
    }

    resize();
    makeParticles();
    window.addEventListener("resize", () => {
      resize();
      makeParticles();
    });

    function tick() {
      ctx.clearRect(0, 0, w, h);
      const maxDist = 130 * devicePixelRatio;

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0 || p.x > w) p.vx *= -1;
        if (p.y < 0 || p.y > h) p.vy *= -1;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = p.gold ? "rgba(207,232,33,0.55)" : "rgba(255,255,255,0.4)";
        ctx.fill();

        for (let j = i + 1; j < particles.length; j++) {
          const q = particles[j];
          const dx = p.x - q.x, dy = p.y - q.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < maxDist) {
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(q.x, q.y);
            ctx.strokeStyle = `rgba(207,232,33,${0.10 * (1 - dist / maxDist)})`;
            ctx.lineWidth = 1;
            ctx.stroke();
          }
        }
      }
      requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }
});
