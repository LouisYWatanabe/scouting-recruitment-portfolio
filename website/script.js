(function () {
  const demoUrl = window.PORTFOLIO_DEMO_URL || "";
  const githubUrl = window.GITHUB_REPO_URL || "#";
  const pdfUrl = window.PDF_BRIEF_URL || "#";

  const iframe = document.getElementById("demo-frame");
  const openDemo = document.querySelectorAll("[data-demo-link]");
  const githubLinks = document.querySelectorAll("[data-github-link]");
  const pdfLinks = document.querySelectorAll("[data-pdf-link]");

  if (iframe && demoUrl && !demoUrl.includes("YOUR-STREAMLIT-SUBDOMAIN")) {
    iframe.src = demoUrl;
    document.getElementById("demo-placeholder").style.display = "none";
    iframe.style.display = "block";
  } else if (iframe) {
    iframe.style.display = "none";
  }

  openDemo.forEach((a) => {
    a.href = demoUrl && !demoUrl.includes("YOUR-STREAMLIT-SUBDOMAIN") ? demoUrl.replace("?embed=true", "") : "#deploy";
  });
  githubLinks.forEach((a) => { a.href = githubUrl; });
  pdfLinks.forEach((a) => { a.href = pdfUrl; });
})();
