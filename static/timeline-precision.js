(() => {
  const factors = [1, 2, 4, 8, 16, 32, 64, 128];
  let timelineFps = 30;
  let viewStart = 0;
  let viewEnd = 0;
  let scaleIndex = 0;
  let pan = null;
  let movingPlayhead = false;
  let rulerStart = NaN;
  let rulerEnd = NaN;
  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
  const frameDuration = () => 1 / clamp(Number(timelineFps) || 30, 1, 240);
  const snapFrame = (t) => clamp(Math.round(t / frameDuration()) * frameDuration(), 0, duration || 0);
  const span = () => Math.max(0.001, viewEnd - viewStart);
  const position = (t) => clamp((t - viewStart) / span(), 0, 1) * 100;
  const timeAt = (clientX) => {
    const rect = timeline.getBoundingClientRect();
    if (!rect.width) return viewStart;
    return snapFrame(viewStart + clamp((clientX - rect.left) / rect.width, 0, 1) * span());
  };
  const visibleCenter = () => duration ? clamp((start + end) / 2, 0, duration) : 0;

  function labelTime(t, interval) {
    const decimals = interval < 0.1 ? 2 : interval < 1 ? 1 : 0;
    const rounded = interval ? Math.round(t / interval) * interval : t;
    const hours = Math.floor(rounded / 3600);
    const minutes = Math.floor((rounded % 3600) / 60);
    const seconds = rounded % 60;
    const sec = seconds.toFixed(decimals).padStart(decimals ? 3 + decimals : 2, '0');
    return hours
      ? `${hours}:${String(minutes).padStart(2, '0')}:${sec}`
      : `${String(minutes).padStart(2, '0')}:${sec}`;
  }

  function drawRuler() {
    if (!duration) return;
    if (Math.abs(rulerStart - viewStart) < 0.000001 && Math.abs(rulerEnd - viewEnd) < 0.000001) return;
    const ruler = $('time-ruler');
    if (!ruler) return;
    ruler.replaceChildren();
    const visible = span();
    const intervals = [0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 180, 240, 300, 600, 900, 1800, 3600];
    const desired = visible / 6;
    const interval = intervals.find((v) => v >= desired) || Math.ceil(desired / 3600) * 3600;
    const marks = [viewStart];
    for (let t = Math.ceil((viewStart + 1e-8) / interval) * interval; t < viewEnd - 1e-8; t += interval) {
      if (t > viewStart + 0.015) marks.push(t);
    }
    if (viewEnd - marks[marks.length - 1] > 0.015) marks.push(viewEnd);
    marks.forEach((t, i) => {
      const mark = document.createElement('div');
      mark.className = `time-mark${i === 0 ? ' first' : ''}${i === marks.length - 1 ? ' last' : ''}`;
      mark.style.left = `${position(t)}%`;
      const label = document.createElement('span');
      label.className = 'time-label';
      label.textContent = labelTime(t, interval);
      const tick = document.createElement('span');
      tick.className = 'time-tick';
      mark.append(label, tick);
      ruler.append(mark);
    });
    rulerStart = viewStart;
    rulerEnd = viewEnd;
  }

  function updateSliderThumb(el, value, label, min, max) {
    el.setAttribute('role', 'slider');
    el.setAttribute('aria-label', label);
    el.setAttribute('aria-valuemin', min.toFixed(3));
    el.setAttribute('aria-valuemax', max.toFixed(3));
    el.setAttribute('aria-valuenow', value.toFixed(3));
    el.setAttribute('aria-valuetext', `${label}: ${fmt(value)}`);
    el.tabIndex = 0;
  }

  function render() {
    if (!duration) return;
    if (viewEnd <= viewStart) { viewStart = 0; viewEnd = duration; }
    start = snapFrame(start);
    end = snapFrame(end);
    const startThumb = $('start-thumb');
    const endThumb = $('end-thumb');
    const cursor = $('playhead');
    startThumb.style.left = `${position(start)}%`;
    endThumb.style.left = `${position(end)}%`;
    const selectedStart = Math.max(start, viewStart);
    const selectedEnd = Math.min(end, viewEnd);
    $('selected').style.left = `${position(selectedStart)}%`;
    $('selected').style.width = `${Math.max(0, position(selectedEnd) - position(selectedStart))}%`;
    cursor.style.left = `${position(video.currentTime || 0)}%`;
    $('start-label').textContent = fmt(start);
    $('end-label').textContent = fmt(end);
    $('clock').textContent = `${fmt(video.currentTime)} / ${fmt(duration)}`;
    const minGap = frameDuration();
    updateSliderThumb(startThumb, start, 'Inicio del tramo', 0, Math.max(0, end - minGap));
    updateSliderThumb(endThumb, end, 'Final del tramo', Math.min(duration, start + minGap), duration);
    const slider = $('time-scale');
    if (slider) slider.value = String(scaleIndex);
    const actualScale = duration / span();
    $('time-scale-readout').textContent = `${actualScale >= 10 ? Math.round(actualScale) : actualScale.toFixed(1)}×`;
    drawRuler();
  }

  function setScale(index, anchor = visibleCenter(), anchorPosition = 0.5) {
    if (!duration) return;
    scaleIndex = clamp(Math.round(index), 0, factors.length - 1);
    const minSpan = Math.min(duration, Math.max(0.25, frameDuration() * 2));
    const newSpan = Math.min(duration, Math.max(minSpan, duration / factors[scaleIndex]));
    anchor = clamp(anchor, 0, duration);
    const startAt = clamp(anchor - clamp(anchorPosition, 0, 1) * newSpan, 0, duration - newSpan);
    viewStart = startAt;
    viewEnd = startAt + newSpan;
    render();
  }

  function shiftWindow(delta) {
    const visible = span();
    viewStart = clamp(viewStart + delta, 0, duration - visible);
    viewEnd = viewStart + visible;
    render();
  }

  window.setTimelineSourceFps = (fps) => {
    const value = Number(fps);
    timelineFps = Number.isFinite(value) && value >= 1 && value <= 240 ? value : 30;
  };
  window.resetTimeline = (videoDuration) => {
    if (Number.isFinite(Number(videoDuration))) duration = Number(videoDuration);
    start = 0;
    end = duration;
    viewStart = 0;
    viewEnd = duration;
    scaleIndex = 0;
    render();
  };

  fmt = (t) => {
    const value = Math.max(0, Number(t) || 0);
    const minutes = Math.floor(value / 60);
    const seconds = (value % 60).toFixed(3).padStart(6, '0');
    return `${String(minutes).padStart(2, '0')}:${seconds}`;
  };
  pct = position;
  drawTimeline = render;
  drawTimeRuler = drawRuler;
  timeFromPointer = (e) => timeAt(e.clientX);
  setPlayhead = (t) => {
    const target = snapFrame(t);
    video.currentTime = target;
    if (target < viewStart || target > viewEnd) setScale(scaleIndex, target, 0.5);
    else render();
  };
  video.onseeked = render;
  video.addEventListener('loadedmetadata', render);

  $('time-zoom-in').addEventListener('click', () => setScale(scaleIndex + 1));
  $('time-zoom-out').addEventListener('click', () => setScale(scaleIndex - 1));
  $('time-fit').addEventListener('click', () => setScale(0, duration / 2));
  $('time-scale').addEventListener('input', (e) => setScale(Number(e.target.value)));
  $('frame-back').addEventListener('click', () => setPlayhead(video.currentTime - frameDuration()));
  $('frame-forward').addEventListener('click', () => setPlayhead(video.currentTime + frameDuration()));

  timeline.addEventListener('wheel', (e) => {
    if (!duration) return;
    e.preventDefault();
    const rect = timeline.getBoundingClientRect();
    const anchorPosition = clamp((e.clientX - rect.left) / rect.width, 0, 1);
    const anchor = viewStart + anchorPosition * span();
    setScale(scaleIndex + (e.deltaY < 0 ? 1 : -1), anchor, anchorPosition);
  }, { passive: false });

  timeline.addEventListener('pointerdown', (e) => {
    if (!e.shiftKey || e.target.closest('.thumb, .playhead')) return;
    pan = { x: e.clientX, start: viewStart, pointerId: e.pointerId };
    timeline.setPointerCapture(e.pointerId);
    e.preventDefault();
    e.stopImmediatePropagation();
  }, true);

  timeline.addEventListener('pointermove', (e) => {
    if (pan && pan.pointerId === e.pointerId) {
      const rect = timeline.getBoundingClientRect();
      const visible = span();
      const offset = (e.clientX - pan.x) / Math.max(1, rect.width) * visible;
      viewStart = clamp(pan.start - offset, 0, duration - visible);
      viewEnd = viewStart + visible;
      render();
      return;
    }
    if (drag === 'start' || drag === 'end') {
      const rect = timeline.getBoundingClientRect();
      const edgeZone = Math.max(14, Math.min(32, rect.width * 0.04));
      if (drag === 'start' && e.clientX < rect.left + edgeZone && viewStart > 0) shiftWindow(-span() * 0.12);
      if (drag === 'end' && e.clientX > rect.right - edgeZone && viewEnd < duration) shiftWindow(span() * 0.12);
      const t = timeAt(e.clientX);
      const gap = frameDuration();
      if (drag === 'start') start = Math.min(t, end - gap);
      else end = Math.max(t, start + gap);
      e.stopImmediatePropagation();
      render();
    }
  }, true);
  timeline.addEventListener('pointerup', (e) => {
    if (pan && pan.pointerId === e.pointerId) pan = null;
  }, true);
  timeline.addEventListener('pointercancel', () => { pan = null; }, true);

  const cursor = $('playhead');
  cursor.addEventListener('pointerdown', (e) => {
    if (!duration) return;
    movingPlayhead = true;
    cursor.setPointerCapture(e.pointerId);
    setPlayhead(timeAt(e.clientX));
    e.preventDefault();
    e.stopPropagation();
  });
  cursor.addEventListener('pointermove', (e) => {
    if (movingPlayhead) setPlayhead(timeAt(e.clientX));
  });
  cursor.addEventListener('pointerup', () => { movingPlayhead = false; });
  cursor.addEventListener('pointercancel', () => { movingPlayhead = false; });

  for (const [id, which] of [['start-thumb', 'start'], ['end-thumb', 'end']]) {
    $(id).addEventListener('keydown', (e) => {
      const delta = frameDuration() * (e.shiftKey ? 10 : 1);
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key)) return;
      e.preventDefault();
      if (which === 'start') {
        start = e.key === 'Home' ? 0 : e.key === 'End' ? end - frameDuration() : clamp(snapFrame(start + (e.key === 'ArrowRight' ? delta : -delta)), 0, end - frameDuration());
      } else {
        end = e.key === 'End' ? duration : e.key === 'Home' ? start + frameDuration() : clamp(snapFrame(end + (e.key === 'ArrowRight' ? delta : -delta)), start + frameDuration(), duration);
      }
      render();
    });
  }

  render();
})();
