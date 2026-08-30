document.addEventListener("DOMContentLoaded", () => {
    // Register ScrollTrigger
    gsap.registerPlugin(ScrollTrigger);

    // 1. Hero Section Animation
    const heroTl = gsap.timeline();
    
    heroTl.from(".hero-subtitle", { y: 20, opacity: 0, duration: 0.8, ease: "power2.out" })
          .from(".hero-title", { y: 30, opacity: 0, duration: 0.8, ease: "power3.out" }, "-=0.5")
          .from(".hero-text", { y: 20, opacity: 0, duration: 0.8, ease: "power2.out" }, "-=0.5")
          .from(".hero-actions", { y: 20, opacity: 0, duration: 0.8, ease: "power2.out" }, "-=0.5")
          .from(".hero-image", { x: 50, opacity: 0, duration: 1.5, ease: "power4.out" }, "-=1");

    // 2. Categories Stagger
    gsap.from(".category-item", {
        scrollTrigger: {
            trigger: ".categories",
            start: "top 85%"
        },
        y: 30,
        opacity: 0,
        duration: 0.6,
        stagger: 0.1,
        ease: "back.out(1.5)"
    });

    // 3. Product Cards Stagger
    gsap.from(".product-card", {
        scrollTrigger: {
            trigger: ".bestsellers",
            start: "top 75%"
        },
        y: 50,
        opacity: 0,
        duration: 0.8,
        stagger: 0.15,
        ease: "power3.out"
    });

    // 4. Promo Cards
    gsap.from(".promo-card", {
        scrollTrigger: {
            trigger: ".promos",
            start: "top 80%"
        },
        scale: 0.95,
        opacity: 0,
        duration: 0.8,
        stagger: 0.2,
        ease: "power2.out"
    });

    // Tab Switching Logic
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelector('.tab.active').classList.remove('active');
            tab.classList.add('active');
            
            // Subtle flash animation when changing categories
            gsap.fromTo(".product-card", 
                { opacity: 0, y: 10 }, 
                { opacity: 1, y: 0, duration: 0.4, stagger: 0.05, ease: "power1.out" }
            );
        });
    });
});