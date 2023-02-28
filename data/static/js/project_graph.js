
(function() {
  // var datasFrame;
  // var target;
  // var projectChart;
  // var domId;
  $.fn.amountGraph = function(sel, datasGraph, id=""){
    // datasFrame = datas;
    // target=sel; //document.getElementById(sel);
    // domId=id;
    var datas= this.data("amountGraph");
    if (!datas) {
        datas = {
            datasFrame: datasGraph,
            target: sel,
            domId:id,
            projectChart:null
        };
        this.data('amountGraph', datas);
    }
    updateGraph(this);
    addBtnListener(this);


    return this;
    

  };
  function addBtnListener(target){
    
      $(target).find('.db_graph_radio_type .radiotab').each(function(){
          $(this).on('change, click', function(){updateGraph(target)});
      })
  };

  function updateGraph(target){
    var datas = $(target).data("amountGraph");

    var typeD= $(target).find("input[name='"+datas.domId+"-tabs']:checked").attr('id').replace(datas.domId+'-tab', '').toLowerCase();
    var typeG= $(target).find("input[name='"+datas.domId+"-graph']:checked").attr('id').replace(datas.domId+'-tab', '').toLowerCase();

    isStacked=(typeG=="stacked")
    //$(this).attr('id').replace('tab', '').toLowerCase();

    var csrftoken = getCookie('csrftoken');
    datasets=createDataSet(datas.datasFrame, typeD, "date", "amount", isStacked, true);

    if(datas.projectChart)datas.projectChart.destroy();
    const dataset = {
        datasets: datasets
      };

    var ctx = $(target).find("#"+datas.domId+'-canvas')[0].getContext('2d');
    datas.projectChart = new Chart(ctx , {
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

        $(target).data('amountGraph', datas);

    }
    

})();


