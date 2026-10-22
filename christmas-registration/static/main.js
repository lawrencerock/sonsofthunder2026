
"use strict";

/* =========================================
   CHRISTMAS REGISTRATION WEBSITE
   Main JavaScript
   ========================================= */

document.addEventListener("DOMContentLoaded", function () {

    /* -------------------------------------
       1. ADMIN PASSWORD VISIBILITY TOGGLE
       ------------------------------------- */

    const togglePassword = document.getElementById("togglePassword");
    const passwordInput = document.getElementById("password");

    if (togglePassword && passwordInput) {
        togglePassword.addEventListener("click", function () {

            const isPassword = passwordInput.type === "password";

            passwordInput.type = isPassword ? "text" : "password";

            togglePassword.textContent = isPassword ? "Hide" : "Show";

            togglePassword.setAttribute(
                "aria-label",
                isPassword ? "Hide password" : "Show password"
            );

            togglePassword.setAttribute(
                "aria-pressed",
                String(isPassword)
            );
        });
    }


    /* -------------------------------------
       2. MOBILE NUMBER INPUT CLEANUP
       ------------------------------------- */

    const mobileInput = document.getElementById("mobile");

    if (mobileInput && mobileInput.type === "tel") {

        mobileInput.addEventListener("input", function () {

            // Keep digits only. The server still performs
            // the authoritative validation.
            const cleanedValue = mobileInput.value.replace(/\D/g, "");

            if (mobileInput.value !== cleanedValue) {
                mobileInput.value = cleanedValue;
            }

            // Limit the field to ten digits.
            if (mobileInput.value.length > 10) {
                mobileInput.value = mobileInput.value.slice(0, 10);
            }
        });
    }


    /* -------------------------------------
       3. REGISTRATION FORM VALIDATION
       ------------------------------------- */

    const registrationForm = document.getElementById("registrationForm");
    const submitButton = document.getElementById("submitButton");

    if (registrationForm && submitButton) {

        registrationForm.addEventListener("submit", function (event) {

            // Use native browser validation first.
            if (!registrationForm.checkValidity()) {
                event.preventDefault();
                registrationForm.reportValidity();
                return;
            }

            const fullName = document.getElementById("full_name");
            const address = document.getElementById("address");

            if (fullName && !fullName.value.trim()) {
                event.preventDefault();
                fullName.setCustomValidity("Please enter your full name.");
                fullName.reportValidity();
                fullName.setCustomValidity("");
                return;
            }

            if (address && !address.value.trim()) {
                event.preventDefault();
                address.setCustomValidity("Please enter your address.");
                address.reportValidity();
                address.setCustomValidity("");
                return;
            }

            // Prevent accidental repeat clicks while the
            // server processes the request.
            if (submitButton.dataset.submitting === "true") {
                event.preventDefault();
                return;
            }

            submitButton.dataset.submitting = "true";
            submitButton.disabled = true;
            submitButton.textContent = "Submitting Registration...";

            // The form continues its normal POST submission.
            // If the request fails, the server must provide
            // an error page or message; the browser cannot
            // guarantee a successful database save.
        });
    }


    /* -------------------------------------
       4. PREVENT ACCIDENTAL EMPTY SEARCH
       ------------------------------------- */

    const searchInput = document.getElementById("search");

    if (searchInput) {
        searchInput.addEventListener("keydown", function (event) {

            if (event.key === "Escape") {
                searchInput.value = "";
            }
        });
    }


    /* -------------------------------------
       5. PRINT CONFIRMATION
       ------------------------------------- */

    const printButton = document.getElementById("printConfirmation");

    if (printButton) {
        printButton.addEventListener("click", function () {
            window.print();
        });
    }

});
