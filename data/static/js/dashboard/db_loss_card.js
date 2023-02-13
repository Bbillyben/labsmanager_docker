var dataFrameLossCard;
var lossChart;
function dblosscard_initCard(dataF){
    dataFrameLossCard=dataF;

    // add listener
    dblosscard_addBtnListener();

    datasets=createDataSet(dataFrameLossCard, "type", "end_date", "amount", true);
    dblosscard_updateGraph(datasets);
}
function dblosscard_addBtnListener(){
    $('#db_losscard_radio_type .radiotab').each(function(){
        $(this).on('change, click', dblosscard_radioListener);
    })
}


function dblosscard_radioListener(e){
    var typeG=$(this).attr('id').replace('tab', '').toLowerCase();
    var csrftoken = getCookie('csrftoken');
    datasets=createDataSet(dataFrameLossCard, typeG, "end_date", "amount", true);
    dblosscard_updateGraph(datasets);
}


function dblosscard_updateGraph(data){
    if(lossChart)lossChart.destroy();
    const dataset = {
        datasets: data
      };


var ctx = document.getElementById('canvas').getContext('2d');
lossChart = new Chart(ctx , {
    type: "line",
    data: dataset, 
    options: {
      responsive: true,
      scales: {
        x: {
          type:'time',
          parsing:'false',      
        },
        y: {
            stacked: true,
            title: {
              display: true,
              text: 'Value'
            }
          }
      }
    }
  });
}
