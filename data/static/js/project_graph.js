var dataFrameProject;
var projectChart;


function project_graph_initCard(dataF){
    dataFrameProject=dataF;

    // add listener
    //dblosscard_addBtnListener();

    projectgraph_updateGraph();
    projectgraph_addBtnListener();
}

function projectgraph_addBtnListener(){
    $('.db_graph_radio_type .radiotab').each(function(){
        $(this).on('change, click', projectgraph_updateGraph);
    })
}

function projectgraph_updateGraph(e=null){
    var typeD= $("input[name='tabs']:checked").attr('id').replace('tab', '').toLowerCase();
    var typeG= $("input[name='graph']:checked").attr('id').replace('tab', '').toLowerCase();

    isStacked=(typeG=="stacked")
    //$(this).attr('id').replace('tab', '').toLowerCase();

    var csrftoken = getCookie('csrftoken');
    datasets=createDataSet(dataFrameProject, typeD, "date", "amount", isStacked, true);

    
    if(projectChart)projectChart.destroy();
    const dataset = {
        datasets: datasets
      };

var ctx = document.getElementById('canvas').getContext('2d');
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