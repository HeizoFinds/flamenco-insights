import { ref, watch, onUnmounted, isRef } from 'vue';

export function useAnimateNumber(targetValue) {
  const displayValue = ref(0);
  let animationFrameId = null;

  const animate = (start, end, duration) => {
    const endValue = Number(end) || 0;
    
    if (start === endValue) {
      displayValue.value = endValue;
      return;
    }
    
    const startTime = performance.now();
    const step = (currentTime) => {
      const elapsedTime = currentTime - startTime;
      const progress = Math.min(elapsedTime / duration, 1);
      
      const easedProgress = 1 - Math.pow(1 - progress, 3);

      displayValue.value = Math.floor(easedProgress * (endValue - start) + start);

      if (progress < 1) {
        animationFrameId = requestAnimationFrame(step);
      } else {
        displayValue.value = endValue;
      }
    };
    animationFrameId = requestAnimationFrame(step);
  };

  const watchSource = targetValue;

  watch(watchSource, (newValue, oldValue) => {
    if (animationFrameId) {
      cancelAnimationFrame(animationFrameId);
    }
    const newNumericValue = Number(newValue) || 0;
    const oldNumericValue = Number(displayValue.value) || 0;
    animate(oldNumericValue, newNumericValue, 1000);
  }, { immediate: true });
  
  onUnmounted(() => {
    if (animationFrameId) {
      cancelAnimationFrame(animationFrameId);
    }
  });

  return {
    displayValue,
  };
}