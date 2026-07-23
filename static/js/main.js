// main.js — students will add JavaScript here as features are built

// Add Expense / Add Income: reveals the "new account" name/type fields
// only when "+ Add a new account…" is selected in the account dropdown.
function toggleNewAccountFields(select) {
    var fields = document.getElementById("new-account-fields");
    if (!fields) return;
    fields.style.display = select.value === "__new__" ? "" : "none";
}

document.addEventListener("DOMContentLoaded", function () {
    var select = document.getElementById("account_id");
    if (select) {
        toggleNewAccountFields(select);
    }
});
