// JS base en puro JavaScript
document.addEventListener('DOMContentLoaded', function(){
  var btn = document.getElementById('sidebarToggle');
  var sidebar = document.getElementById('sidebar');
  var main = document.getElementById('mainContent');
  if(btn && sidebar){
    btn.addEventListener('click', function(){
      sidebar.classList.toggle('collapsed');
      if(sidebar.classList.contains('collapsed')){
        sidebar.style.display = 'none';
      } else {
        sidebar.style.display = '';
      }
    });
  }

  // Helper para renderizar datos de ejemplo si se usa fetch
  window.renderTableRows = function(tbodyId, rows){
    var tbody = document.querySelector(tbodyId);
    if(!tbody) return;
    tbody.innerHTML = '';
    rows.forEach(function(r){
      var tr = document.createElement('tr');
      tr.innerHTML = '<td>'+ (r.id||'') +'</td>'+
                     '<td>'+ (r.name||'') +'</td>'+
                     '<td>'+ (r.date||'') +'</td>'+
                     '<td>'+ (r.status||'') +'</td>';
      tbody.appendChild(tr);
    });
  };

    // Si la plantilla específica incluye un `patient-sidebar`, reemplazamos el sidebar base
    (function replacePatientSidebar(){
      try {
        var patientSidebar = document.getElementById('patient-sidebar');
        var baseSidebar = document.getElementById('sidebar');
        var baseMain = document.getElementById('mainContent');
        if (patientSidebar && baseSidebar) {
          // Copiamos el contenido del sidebar del paciente al sidebar base
          baseSidebar.innerHTML = patientSidebar.innerHTML;
          // Removemos el sidebar interno para evitar duplicados
          patientSidebar.parentNode && patientSidebar.parentNode.removeChild(patientSidebar);

          // Si existe un layout interno con .main-content (anidado), movemos sus hijos a #mainContent
          var innerLayout = baseMain.querySelector('.layout');
          if (innerLayout) {
            var innerMain = innerLayout.querySelector('.main-content');
            if (innerMain) {
              // Mover todos los hijos de innerMain a baseMain
              while (innerMain.firstChild) {
                baseMain.appendChild(innerMain.firstChild);
              }
            }
            // limpiar el contenedor vacío
            innerLayout.parentNode && innerLayout.parentNode.removeChild(innerLayout);
          }
        }
      } catch (e) {
        console.warn('replacePatientSidebar failed', e);
      }
    })();
});
