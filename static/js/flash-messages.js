(() => {
  const CLOSE_DELAY_MS = 5000;
  const HIDE_TRANSITION_MS = 260;

  const closeFlash = (element) => {
    if (!element || element.dataset.closing === "true") {
      return;
    }

    element.dataset.closing = "true";
    element.classList.add("is-closing");

    window.setTimeout(() => {
      element.classList.add("is-hidden");

      window.setTimeout(() => {
        element.remove();
      }, HIDE_TRANSITION_MS);
    }, 10);
  };

  const enhanceFlashMessage = (element) => {
    if (!element || element.dataset.flashEnhanced === "true") {
      return;
    }

    element.dataset.flashEnhanced = "true";
    const closeButton = element.querySelector("[data-flash-close]");

    if (closeButton) {
      closeButton.addEventListener("click", () => {
        closeFlash(element);
      });
    }

    window.setTimeout(() => {
      closeFlash(element);
    }, CLOSE_DELAY_MS);
  };

  window.EasySportFlashMessages = {
    enhanceFlashMessage,
  };

  document.querySelectorAll("[data-flash-message]").forEach((element) => {
    enhanceFlashMessage(element);
  });
})();
