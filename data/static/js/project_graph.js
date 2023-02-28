
(function() {
  var datasFrame;
  var target;
  var projectChart;
  var domId;
  $.fn.amountGraph = function(sel, datas, id=""){
    datasFrame = datas;
    target=sel; //document.getElementById(sel);
    domId=id;
    
    updateGraph();
    addBtnListener();


    return this;
    

  };
  function addBtnListener(){
      $(target).find('.db_graph_radio_type .radiotab').each(function(){
          $(this).on('change, click', updateGraph);
      })
  };

  function updateGraph(e=null){
  

    var typeD= $(target).find("input[name='"+domId+"-tabs']:checked").attr('id').replace(domId+'-tab', '').toLowerCase();
    var typeG= $(target).find("input[name='"+domId+"-graph']:checked").attr('id').replace(domId+'-tab', '').toLowerCase();

    isStacked=(typeG=="stacked")
    //$(this).attr('id').replace('tab', '').toLowerCase();

    var csrftoken = getCookie('csrftoken');
    datasets=createDataSet(datasFrame, typeD, "date", "amount", isStacked, true);

    
    if(projectChart)projectChart.destroy();
    const dataset = {
        datasets: datasets
      };
    var ctx = $(target).find("#"+domId+'-canvas')[0].getContext('2d');
    projectChart = new Chart(ctx , {
        type: "line",
        data: dataset, 
        options: {
          responsive: true,
          scales: {
            x: {
              type:'time',
              parsing:'false',
              time: {
                unit:'month',
                unitStepSize: 1,
                displayFormats: {
                  'month': 'MMM yy'
                }
              }      
            },
            y: {
                stacked: isStacked,
                title: {
                  display: true,
                  text: 'Value'
                }
              },    
          }
        }
      });
  }

})();


