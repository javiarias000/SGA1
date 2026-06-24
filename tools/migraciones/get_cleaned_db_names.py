from students.models import Student

output_file_path = '/Users/javi000/.gemini/tmp/7ee9fa71869d40ada58c077b7bcaa473e114dee96207822bb48088c40085b528/db_student_names_cleaned.txt'

with open(output_file_path, 'w', encoding='utf-8') as outfile:
    for s in Student.objects.all():
        cleaned_name = s.name.rsplit(' - ', 1)[0].strip()
        outfile.write(cleaned_name + '\n')
print(f"Extracted cleaned student names to {output_file_path}")
