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
});
