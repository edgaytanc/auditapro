(function(){"use strict";
 const root=document.querySelector('.financial-company-inline');
 const input=document.getElementById('financialCompanyName');
 const button=document.getElementById('financialCompanySave');
 const feedback=document.getElementById('financialCompanyFeedback');
 if(!root||!input||!button)return;
 window.financialDashboardCompany=()=>input.value.trim();
 const csrf=()=>{const c=document.cookie.split('; ').find(x=>x.startsWith('csrftoken='));return c?decodeURIComponent(c.split('=').slice(1).join('=')):'';};
 button.addEventListener('click',async function(){
   const company=input.value.trim();if(!company){feedback.textContent='Indica el nombre de la entidad.';return;}
   button.disabled=true;feedback.textContent='Guardando…';
   try{
    const res=await fetch(root.dataset.saveUrl,{method:'POST',credentials:'same-origin',headers:{'X-CSRFToken':csrf(),'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({company_name:company})});
    const data=await res.json();if(!res.ok)throw new Error(data.error||'No se pudo guardar');
    feedback.textContent='Nombre guardado';
    document.dispatchEvent(new CustomEvent('financial-company-saved',{detail:{company_name:data.company_name}}));
   }catch(e){feedback.textContent=e.message;}finally{button.disabled=false;}
 });
})();
