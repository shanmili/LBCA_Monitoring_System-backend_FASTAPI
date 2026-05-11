import psycopg2

try:
    conn = psycopg2.connect(
        host='localhost',
        user='postgres',
        password='laninamitevasco',
        database='lbca_db'
    )
    cur = conn.cursor()
    
    # Query with JOIN to get teacher, subject, and section names
    query = """
    SELECT 
        cs.class_schedule_id,
        sy.year as school_year,
        sec.name as section_name,
        sub.subject_name,
        CONCAT(st.first_name, ' ', st.last_name) as teacher_name,
        cs.day_of_week,
        cs.start_time,
        cs.end_time,
        cs.room,
        cs.created_at
    FROM class_schedules cs
    LEFT JOIN school_years sy ON cs.school_year_id = sy.school_year_id
    LEFT JOIN sections sec ON cs.section_id = sec.section_id
    LEFT JOIN subjects sub ON cs.subject_id = sub.subject_id
    LEFT JOIN staff st ON cs.teacher_id = st.id
    ORDER BY cs.class_schedule_id DESC;
    """
    
    cur.execute(query)
    rows = cur.fetchall()
    
    if rows:
        print(f'\n{"="*140}')
        print(f'SAVED SCHEDULES IN DATABASE - Total: {len(rows)}')
        print(f'{"="*140}\n')
        for i, row in enumerate(rows, 1):
            print(f"Schedule #{i}")
            print(f"  Schedule ID        : {row[0]}")
            print(f"  School Year        : {row[1]}")
            print(f"  Section            : {row[2]}")
            print(f"  Subject            : {row[3]}")
            print(f"  Teacher            : {row[4]}")
            print(f"  Day of Week        : {row[5]}")
            print(f"  Time               : {row[6]} - {row[7]}")
            print(f"  Room               : {row[8]}")
            print(f"  Saved On           : {row[9]}")
            print(f'{"-"*140}\n')
    else:
        print('No schedules found in the database.')
    
    cur.close()
    conn.close()
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
