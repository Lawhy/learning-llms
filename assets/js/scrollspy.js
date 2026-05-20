// Scrollspy: highlights the section the reader is currently in, drives the
// animated dot marker, and locks the active state when the user clicks a TOC
// link so the marker doesn't bounce around during the smooth scroll.

(function () {
  const tocLinks = document.querySelectorAll('.left-toc a[data-toc]');
  // Resolve target elements from TOC link hrefs so this works for both
  // the homepage (#section ids) and post pages (#heading ids).
  const sections = [...tocLinks]
    .map((a) => document.getElementById(a.getAttribute('href').replace(/^#/, '')))
    .filter(Boolean);
  const marker = document.querySelector('.toc-marker');
  const tocEl = document.querySelector('.left-toc');
  if (!sections.length || !tocLinks.length) return;

  const linkById = new Map();
  tocLinks.forEach((a) => {
    const id = a.getAttribute('href').replace(/^#/, '');
    linkById.set(id, a);
  });

  let activeId = null;
  let lockedId = null;
  let lockTimer = null;

  const moveMarker = (link) => {
    if (!marker || !link || !tocEl) return;
    const linkBox = link.getBoundingClientRect();
    const tocBox = tocEl.getBoundingClientRect();
    const top = linkBox.top - tocBox.top + linkBox.height / 2 - 2.5; // center 5px dot
    marker.style.transform = `translateY(${top}px)`;
    marker.classList.add('is-visible');
  };

  const setActive = (id, force = false) => {
    if (lockedId && !force && id !== lockedId) return;
    if (id === activeId) return;
    activeId = id;
    tocLinks.forEach((a) => a.classList.remove('is-active'));
    const link = linkById.get(id);
    if (link) {
      link.classList.add('is-active');
      moveMarker(link);
    }
  };

  const lockActive = (id) => {
    lockedId = id;
    setActive(id, true);
    clearTimeout(lockTimer);
    lockTimer = setTimeout(() => {
      lockedId = null;
      // If the user has stopped scrolling before the lock expired, no scroll
      // event will fire to re-check. Resync once with current scroll position.
      updateActive();
    }, 1500);
  };

  // Force-activate on TOC click so IO/scrollspy can't pull the marker off
  // the target during smooth-scroll.
  tocLinks.forEach((link) => {
    link.addEventListener('click', () => {
      const id = link.getAttribute('href').replace(/^#/, '');
      lockActive(id);
    });
  });

  // Pick the LAST section whose top has crossed the activation line (30% from
  // top of viewport). This gives a reliable "which section is the reader in"
  // signal — including short final sections that IntersectionObserver misses.
  const updateActive = () => {
    const scrollLine = window.innerHeight * 0.30;
    let candidate = sections[0];
    sections.forEach((s) => {
      if (s.getBoundingClientRect().top <= scrollLine) {
        candidate = s;
      }
    });

    // Bottom-of-page guarantee: always activate the last section when within
    // 40px of the doc bottom.
    const scrollBottom = window.innerHeight + window.scrollY;
    const docBottom = document.documentElement.scrollHeight;
    if (scrollBottom >= docBottom - 40) {
      candidate = sections[sections.length - 1];
    }

    if (candidate) setActive(candidate.id);
  };

  let ticking = false;
  window.addEventListener(
    'scroll',
    () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        updateActive();
        ticking = false;
      });
    },
    { passive: true }
  );

  // Recompute marker position on resize (link layout can shift).
  window.addEventListener('resize', () => {
    const link = linkById.get(activeId);
    if (link) moveMarker(link);
    updateActive();
  });

  // First paint
  updateActive();
})();

// Margin-note markers sit visually next to their notes (right gutter on
// desktop, inline callout on mobile), so the default anchor-jump behaviour
// just yanks the page around for no reason. Swallow the click.
(function () {
  document.addEventListener('click', (e) => {
    const a = e.target.closest('.margin-marker a');
    if (a) e.preventDefault();
  });
})();
