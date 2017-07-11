$(document).ready(function() {

		$('body').on('click','.app_name',function(event) {
			var settingName = $(event.currentTarget).attr('setting');
			$('.selected').removeClass('selected');
			$(event.currentTarget).addClass('selected');
			$('.show').addClass('o_hidden').removeClass('show');
			$('.' + settingName + '_setting_view').addClass('show').removeClass('o_hidden');
		});

});
