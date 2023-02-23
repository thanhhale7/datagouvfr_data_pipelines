from airflow import DAG
from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.utils.dates import days_ago

with DAG(
    dag_id='data_processing_sirene_geocodage',
    schedule_interval='48 7 1 * *',
    start_date=days_ago(31),
    tags=["data_processing", "sirene", "geocodage", "etalab" 'geocodage'],
    params={},
) as dag:

    start_addok = SSHOperator(
        ssh_conn_id="SSH_DATAENG_ETALAB_STUDIO",
        task_id="start_addok",
        command=(
            "cd /srv/sirene/addok-docker/ && docker-compose -f docker-compose-ban-poi.yml up "
            "--scale addok-ban=6 --scale addok-redis-ban=6 -d"
        ),
        dag=dag
    )

    wait_addok_to_be_ready = SSHOperator(
        ssh_conn_id="SSH_DATAENG_ETALAB_STUDIO",
        task_id="wait_addok_to_be_ready",
        command="sleep 120",
        dag=dag
    )

    download_last_sirene_batch = SSHOperator(
        ssh_conn_id="SSH_DATAENG_ETALAB_STUDIO",
        task_id="download_last_sirene_batch",
        command="/srv/sirene/geocodage-sirene/1_download_last_sirene_batch.sh ",
        dag=dag
    )

    split_departments_files = SSHOperator(
        ssh_conn_id="SSH_DATAENG_ETALAB_STUDIO",
        task_id="split_departments_files",
        command="/srv/sirene/geocodage-sirene/2_split_departments_files.sh ",
        dag=dag
    )

    geocoding = SSHOperator(
        ssh_conn_id="SSH_DATAENG_ETALAB_STUDIO",
        task_id="geocoding",
        command="/srv/sirene/geocodage-sirene/3_geocoding_by_increasing_size.sh ",
        dag=dag
    )

    split_by_locality = SSHOperator(
        ssh_conn_id="SSH_DATAENG_ETALAB_STUDIO",
        task_id="split_by_locality",
        command="/srv/sirene/geocodage-sirene/4a_split_by_locality.sh ",
        dag=dag)

    get_geocode_stats = SSHOperator(
        ssh_conn_id="SSH_DATAENG_ETALAB_STUDIO",
        task_id="get_geocode_stats",
        command="/srv/sirene/geocodage-sirene/4b_geocode_stats.sh ",
        dag=dag)

    shutdown_addok = SSHOperator(
        ssh_conn_id="SSH_DATAENG_ETALAB_STUDIO",
        task_id="shutdown_addok",
        command="cd /srv/sirene/addok-docker/ && docker-compose down --remove-orphans ",
        dag=dag)

    national_files_agregation = SSHOperator(
        ssh_conn_id="SSH_DATAENG_ETALAB_STUDIO",
        task_id="national_files_agregation",
        command="/srv/sirene/geocodage-sirene/5_national_files_agregation.sh ",
        dag=dag)

    prepare_to_rsync = SSHOperator(
        ssh_conn_id="SSH_DATAENG_ETALAB_STUDIO",
        task_id="prepare_to_rsync",
        command="/srv/sirene/geocodage-sirene/6_prepare_to_rsync.sh ",
        dag=dag)

    rsync_to_files_data_gouv = SSHOperator(
        ssh_conn_id="SSH_DATAENG_ETALAB_STUDIO",
        task_id="rsync_to_files_data_gouv",
        command="/srv/sirene/geocodage-sirene/7_rsync_to_files_data_gouv.sh ",
        dag=dag)

    mkdir_last_and_symbolic_links = SSHOperator(
        ssh_conn_id="SSH_FILES_DATA_GOUV_FR",
        task_id="mkdir_last_and_symbolic_links",
        command=(
            r"cd /srv/nfs/files.data.gouv.fr/geo-sirene/ && rm -rf last/* && rm -rf last && "
            r"mkdir last && cd $(date +%Y-%m)/ && find . \( ! -regex '\.' \) -type d -exec "
            r"mkdir /srv/nfs/files.data.gouv.fr/geo-sirene/last/{} \; && find * -type f -exec "
            r"ln -s `pwd`/{} /srv/nfs/files.data.gouv.fr/geo-sirene/last/{} \;"
        ),
        dag=dag)

    wait_addok_to_be_ready.set_upstream(start_addok)
    download_last_sirene_batch.set_upstream(wait_addok_to_be_ready)
    split_departments_files.set_upstream(download_last_sirene_batch)
    geocoding.set_upstream(split_departments_files)
    split_by_locality.set_upstream(geocoding)
    get_geocode_stats.set_upstream(geocoding)
    shutdown_addok.set_upstream(geocoding)
    national_files_agregation.set_upstream(geocoding)
    prepare_to_rsync.set_upstream(national_files_agregation)
    prepare_to_rsync.set_upstream(split_by_locality)
    prepare_to_rsync.set_upstream(get_geocode_stats)
    rsync_to_files_data_gouv.set_upstream(prepare_to_rsync)
    mkdir_last_and_symbolic_links.set_upstream(rsync_to_files_data_gouv)
