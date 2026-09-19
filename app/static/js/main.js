document.addEventListener("DOMContentLoaded", () => {

    /*
     * =========================================================
     * MOBILE SIDEBAR
     * =========================================================
     */

    const menuToggle = document.getElementById("menu-toggle");
    const sidebar = document.getElementById("app-sidebar");

    if (menuToggle && sidebar) {

        menuToggle.addEventListener("click", () => {

            const isOpen = sidebar.classList.toggle("open");

            menuToggle.setAttribute(
                "aria-expanded",
                String(isOpen)
            );

        });


        /*
         * Close sidebar after selecting a navigation item
         * on smaller screens.
         */

        sidebar.querySelectorAll("a").forEach((link) => {

            link.addEventListener("click", () => {

                if (window.innerWidth <= 900) {

                    sidebar.classList.remove("open");

                    menuToggle.setAttribute(
                        "aria-expanded",
                        "false"
                    );

                }

            });

        });

    }


    /*
     * =========================================================
     * FLASH MESSAGE DISMISSAL
     * =========================================================
     */

    const flashMessages =
        document.querySelectorAll(".flash");

    flashMessages.forEach((flash) => {

        const closeButton =
            flash.querySelector(".flash-close");


        if (closeButton) {

            closeButton.addEventListener(
                "click",
                () => {
                    flash.remove();
                }
            );

        }


        /*
         * Automatically remove flash messages
         * after approximately four seconds.
         */

        window.setTimeout(() => {

            if (flash && flash.isConnected) {
                flash.remove();
            }

        }, 4000);

    });


    /*
     * =========================================================
     * PREVENT DOUBLE FORM SUBMISSION
     * =========================================================
     */

    document.querySelectorAll("form").forEach((form) => {

        form.addEventListener("submit", () => {

            const submitButton =
                form.querySelector(
                    'button[type="submit"], input[type="submit"]'
                );

            if (!submitButton) {
                return;
            }

            /*
             * Don't disable buttons that are explicitly marked
             * as allowing repeated submission.
             */

            if (
                submitButton.dataset.allowRepeat === "true"
            ) {
                return;
            }

            /*
             * Small delay so the browser still performs the
             * normal form submission reliably.
             */

            window.setTimeout(() => {

                submitButton.disabled = true;

            }, 10);

        });

    });

});