const input = document.getElementById('password');
   
input.addEventListener('input', function onInput() {
  // Check if the input's value is an empty string

  /* verificar comprimento */
  if (input.value.trim().length <8) {
    //input.style.backgroundColor = 'lightcoral';
    document.getElementById('password-rule-1').style.color="white";
  } else {
    //input.style.backgroundColor = 'lightgreen';
    document.getElementById('password-rule-1').style.color="#7b7bfe";
  }
  /*verificar maiúscula*/
  if (/[A-ZÀ-Ú]/.test(input.value)) document.getElementById('password-rule-2').style.color="#7979e3";
  else document.getElementById('password-rule-2').style.color="white";

 /*verificar minúscula*/
  if (/[a-zà-ú]/.test(input.value)) document.getElementById('password-rule-3').style.color="#7979e3";
  else document.getElementById('password-rule-3').style.color="white";
    

   if (/[0-9]/.test(input.value)) document.getElementById('password-rule-4').style.color="#7979e3";
   else document.getElementById('password-rule-4').style.color="white";

   if(/[@$!%*#?&+-]/.test(input.value)) document.getElementById('password-rule-5').style.color="#7979e3";
   else document.getElementById('password-rule-5').style.color="white";

   if(/[A-Za-z\d@$!%*#?&+-]/.test(input.value)) document.getElementById('password-rule-6').style.color="#7979e3";
   else document.getElementById('password-rule-6').style.color="white";
});




const passwordInput = document.getElementById("password");
const togglePasswordBtn = document.getElementById("togglePassword");

togglePasswordBtn.addEventListener("click", () => {
  const isPassword = passwordInput.type === "password";

  passwordInput.type = isPassword ? "text" : "password";
  togglePasswordBtn.textContent = isPassword ? "Esconder" : "Mostrar";
});